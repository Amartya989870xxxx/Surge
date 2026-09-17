"""Runs scenarios end-to-end through the real orchestrator against seeded worlds, then scores them.

Usage: python -m app.evaluation.runner [--reasoning heuristic|llm] [--scenarios id1,id2] [--fail-under 0.9]
"""

import argparse
import asyncio
import logging
import sys
import time
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models import (
    Action,
    Claim,
    EvaluationRun,
    EvaluationSuite,
    EvidenceItem,
    Investigation,
    InvestigationEvent,
    new_id,
)
from app.enums import ApprovalMode, ApprovalStatus, ConnectorMode, ExecutionMode, InvestigationStatus, ReasoningMode
from app.errors import ErrorCode, SurgeAPIError
from app.evaluation.metrics import aggregate, score_scenario
from app.evaluation.reports import render_text, write_report_files
from app.scenarios import Scenario

logger = logging.getLogger("surge.evaluation")

_RUN_FIELDS = [
    "scenario_id", "category", "investigation_ids", "expected_hypothesis", "predicted_hypothesis",
    "diagnosis_correct", "evidence_precision", "evidence_recall", "grounded_claim_rate", "unsupported_claim_count",
    "claim_count", "expected_action", "action_taken", "action_success", "verification_success",
    "duplicate_action_count", "mutation_attempts", "tool_calls", "tool_failures", "recovery_expected",
    "recovery_success", "approval_respected", "confidence", "correctness", "latency_ms", "passed",
    "failure_reasons", "details",
]


def _llm_usage(llm) -> list[dict] | None:
    if not hasattr(llm, "status"):
        return None
    return [
        {"model": m["label"], "calls": m["calls"], "successes": m["successes"], "failures": m["failures"]}
        for m in llm.status()["models"]
        if m["calls"]
    ]


class EvaluationRunner:
    def __init__(self, services):
        self.s = services

    def create_suite(self, reasoning: ReasoningMode | str, scenario_ids: list[str] | None = None) -> str:
        s = self.s
        reasoning = ReasoningMode(reasoning)
        try:
            scenarios = [s.library.get(i) for i in scenario_ids] if scenario_ids else s.library.list()
        except KeyError as exc:
            raise SurgeAPIError(ErrorCode.NOT_FOUND, f"Unknown scenario {exc.args[0]!r}", http_status=404) from exc
        if not scenarios:
            raise SurgeAPIError(ErrorCode.INVALID_REQUEST, "No evaluation scenarios found", http_status=422)
        if reasoning == ReasoningMode.LLM and not s.llm.available:
            raise SurgeAPIError(
                ErrorCode.INVALID_STATE, "LLM evaluation requested but no Groq or Gemini API key is configured", http_status=409
            )
        suite_id = new_id("eval")
        with s.db.session() as db:
            db.add(
                EvaluationSuite(
                    id=suite_id,
                    status="running",
                    reasoning_mode=reasoning.value,
                    agent_version=s.settings.version,
                    scenario_ids=[x.scenario_id for x in scenarios],
                )
            )
        return suite_id

    async def run_suite(self, suite_id: str) -> dict:
        s = self.s
        with s.db.session() as db:
            suite = db.get(EvaluationSuite, suite_id)
            scenario_ids = list(suite.scenario_ids)
            reasoning = ReasoningMode(suite.reasoning_mode)
        results = []
        try:
            for scenario_id in scenario_ids:
                result = await self.run_scenario(suite_id, s.library.get(scenario_id), reasoning)
                results.append(result)
                self._store_run(suite_id, reasoning, result)
            report = aggregate(
                results,
                suite_id=suite_id,
                reasoning_mode=reasoning.value,
                agent_version=s.settings.version,
                model=getattr(s.llm, "description", s.llm.model) if reasoning == ReasoningMode.LLM else None,
                llm_usage=_llm_usage(s.llm) if reasoning == ReasoningMode.LLM else None,
            )
            text = render_text(report)
            with s.db.session() as db:
                suite = db.get(EvaluationSuite, suite_id)
                suite.status = "completed"
                suite.completed_at = datetime.now(UTC)
                suite.report = report
                suite.report_text = text
            try:
                write_report_files(s.settings.reports_dir, report, text)
            except OSError:
                logger.warning("Could not write report files to %s", s.settings.reports_dir)
            return report
        except Exception as exc:
            logger.exception("Evaluation suite %s failed", suite_id)
            with s.db.session() as db:
                suite = db.get(EvaluationSuite, suite_id)
                suite.status = "failed"
                suite.completed_at = datetime.now(UTC)
                suite.error = {"code": ErrorCode.INTERNAL.value, "message": f"{type(exc).__name__}: {exc}"[:500]}
            raise

    async def run_scenario(self, suite_id: str, scenario: Scenario, reasoning: ReasoningMode) -> dict:
        s = self.s
        world = s.library.build_world(scenario)
        world_key = f"eval:{suite_id}:{scenario.scenario_id}"
        s.worlds.put(world_key, world)
        inv_ids: list[str] = []
        started = time.perf_counter()
        try:
            for _ in range(max(1, scenario.repeat)):
                inv_id = s.orchestrator.create_investigation(
                    request=scenario.request,
                    time_range=scenario.time_range,
                    connector_mode=ConnectorMode.DEMO,
                    scenario_id=scenario.scenario_id,
                    faults=scenario.faults,
                    approval_mode=ApprovalMode.REQUIRED,
                    reasoning=reasoning,
                    execution_mode=ExecutionMode.EVALUATION,
                    world_key=world_key,
                    latency_ms=0,
                    session_id=f"eval:{suite_id}",
                )
                inv_ids.append(inv_id)
                await s.orchestrator.run(inv_id)
                if s.lifecycle.status(inv_id) == InvestigationStatus.AWAITING_APPROVAL:
                    with s.db.session() as db:
                        pending = db.scalar(
                            select(Action.id).where(
                                Action.investigation_id == inv_id,
                                Action.approval_status == ApprovalStatus.PENDING.value,
                            )
                        )
                    approve = scenario.approval == "approve"
                    await s.orchestrator.decide_action(
                        inv_id, pending, approve, decided_by="evaluation-harness", schedule=False
                    )
                    if approve:
                        await s.orchestrator.run_action(inv_id, pending)
            latency = int((time.perf_counter() - started) * 1000)
            invs, evidence, claims, actions, events = self._load(inv_ids)
            return score_scenario(scenario, invs, evidence, claims, actions, events, world, latency)
        finally:
            for inv_id in inv_ids:
                s.runtime.forget(inv_id)
            s.worlds.reset(world_key)

    def _load(self, inv_ids: list[str]):
        with self.s.db.session() as db:
            invs = [db.get(Investigation, i) for i in inv_ids]

            def grouped(model, order):
                out = {i: [] for i in inv_ids}
                rows = db.scalars(select(model).where(model.investigation_id.in_(inv_ids)).order_by(order)).all()
                for row in rows:
                    out[row.investigation_id].append(row)
                return out

            evidence = grouped(EvidenceItem, EvidenceItem.relevance_score.desc())
            claims = grouped(Claim, Claim.position)
            actions = grouped(Action, Action.created_at)
            events = grouped(InvestigationEvent, InvestigationEvent.sequence)
            db.expunge_all()
        return invs, evidence, claims, actions, events

    def _store_run(self, suite_id: str, reasoning: ReasoningMode, result: dict) -> None:
        with self.s.db.session() as db:
            db.add(
                EvaluationRun(
                    id=new_id("evr"),
                    suite_id=suite_id,
                    agent_version=self.s.settings.version,
                    reasoning_mode=reasoning.value,
                    **{k: result[k] for k in _RUN_FIELDS},
                )
            )


def main(argv: list[str] | None = None) -> None:
    from app.config import get_settings
    from app.observability.logging import configure_logging
    from app.services import build_services

    parser = argparse.ArgumentParser(description="Run the Surge scenario evaluation suite")
    parser.add_argument("--reasoning", choices=["heuristic", "llm"], default="heuristic")
    parser.add_argument("--scenarios", help="Comma-separated scenario ids (default: all)")
    parser.add_argument("--fail-under", type=float, default=None, help="Exit 1 if end-to-end success rate is below this")
    args = parser.parse_args(argv)
    configure_logging("WARNING")

    async def _run() -> dict:
        services = build_services(get_settings())
        try:
            suite_id = services.evaluations.create_suite(
                ReasoningMode(args.reasoning), args.scenarios.split(",") if args.scenarios else None
            )
            report = await services.evaluations.run_suite(suite_id)
            print(render_text(report))
            print(f"\nReport files: {services.settings.reports_dir}/{suite_id}.json (.md)")
            return report
        finally:
            await services.aclose()

    report = asyncio.run(_run())
    rate = report["headline"]["end_to_end_success"]["rate"] or 0.0
    if args.fail_under is not None and rate < args.fail_under:
        sys.exit(1)


if __name__ == "__main__":
    main()
