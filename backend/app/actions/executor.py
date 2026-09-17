"""Executes an approved mutation exactly once, recovers from ambiguous failures by checking
provider state before retrying, then independently verifies the side effect."""

from datetime import UTC, datetime

from app.actions.idempotency import IdempotencyLedger, action_marker
from app.actions.verification import (
    VerificationResult,
    find_comment_by_marker,
    find_issue_by_marker,
    verify_comment,
    verify_issue,
)
from app.agent.state import Lifecycle
from app.db.models import Action, Verification, new_id
from app.db.session import Database
from app.enums import (
    ApprovalStatus,
    EventType,
    ExecutionStatus,
    InvestigationStatus,
    VerificationStatus,
)
from app.enums import Actor
from app.observability.events import EventBus
from app.tools.base import ToolContext
from app.tools.runner import ToolRunner

MAX_MUTATION_ATTEMPTS = 2


class ActionExecutor:
    def __init__(self, db: Database, bus: EventBus, runner: ToolRunner, ledger: IdempotencyLedger, lifecycle: Lifecycle):
        self.db = db
        self.bus = bus
        self.runner = runner
        self.ledger = ledger
        self.lifecycle = lifecycle

    def _update(self, action_id: str, **fields) -> Action:
        with self.db.session() as s:
            action = s.get(Action, action_id)
            for k, v in fields.items():
                setattr(action, k, v)
            s.flush()
            s.expunge(action)
            return action

    async def execute(self, investigation_id: str, action_id: str, connectors) -> Action:
        with self.db.session() as s:
            action = s.get(Action, action_id)
            s.expunge(action)
        if action.approval_required and action.approval_status != ApprovalStatus.APPROVED:
            raise PermissionError("Action has not been approved")

        ctx = ToolContext(investigation_id, connectors, approved_action_id=action.id)
        key = action.idempotency_key
        marker = action_marker(key)
        succeeded = False

        entry = self.ledger.get(key)
        if action.execution_status == ExecutionStatus.SUCCEEDED or (entry and entry.status == "SUCCEEDED"):
            ext = action.external_result_id or (entry.external_result_id if entry else None)
            self.bus.publish(
                investigation_id, EventType.IDEMPOTENT_REPLAY,
                f"Already executed (idempotency key {key[:12]}…); no new mutation sent",
                actor=Actor.SYSTEM, action_id=action.id, external_app=action.external_app,
                summary=f"Existing result: {ext}", data={"idempotency_key": key, "external_result_id": ext},
            )
            action = self._update(
                action.id, execution_status=ExecutionStatus.SUCCEEDED.value,
                external_result_id=ext, external_url=action.external_url or (entry.external_url if entry else None),
            )
            succeeded = True
        elif entry and entry.status in ("UNKNOWN", "IN_PROGRESS"):
            self.bus.publish(
                investigation_id, EventType.ACTION_AMBIGUOUS,
                "A previous attempt ended ambiguously; checking provider state before retrying",
                actor=Actor.SYSTEM, action_id=action.id, external_app=action.external_app, status="checking",
            )
            found, ok = await self._lookup(ctx, action, marker)
            if found:
                action = self._record_success(investigation_id, action, key, found, recovered=True)
                succeeded = True
            elif not ok:
                return self._mark_unknown(investigation_id, action, "Provider state could not be checked; not retrying blindly")

        if not succeeded:
            action = self._update(action.id, execution_status=ExecutionStatus.EXECUTING.value)
            self.bus.publish(
                investigation_id, EventType.ACTION_EXECUTING, f"Executing: {action.title}",
                actor=Actor.AGENT, action_id=action.id, external_app=action.external_app, status="running",
                data={"idempotency_key": key, "marker": marker, "action_type": action.action_type},
            )
            tool, args = self._tool_call(action)
            for attempt in range(1, MAX_MUTATION_ATTEMPTS + 1):
                self.ledger.begin(key, action.id)
                action = self._update(action.id, attempts=attempt)
                res = await self.runner.call(ctx, tool, args, purpose=action.title)
                if res.success:
                    action = self._record_success(investigation_id, action, key, res.data, recovered=False)
                    succeeded = True
                    break
                if res.error.ambiguous:
                    self.ledger.resolve(key, "UNKNOWN")
                    self.bus.publish(
                        investigation_id, EventType.ACTION_AMBIGUOUS,
                        f"{res.error.code}: outcome unknown, the provider may have applied the change",
                        actor=Actor.SYSTEM, action_id=action.id, external_app=action.external_app, status="checking",
                        summary=f"Searching for marker {marker} before any retry, to avoid a duplicate.",
                        error_code=res.error.code,
                    )
                    found, ok = await self._lookup(ctx, action, marker)
                    if found:
                        action = self._record_success(investigation_id, action, key, found, recovered=True)
                        succeeded = True
                        break
                    if not ok:
                        return self._mark_unknown(investigation_id, action, "Could not confirm provider state after an ambiguous failure")
                    if attempt < MAX_MUTATION_ATTEMPTS:
                        self.bus.publish(
                            investigation_id, EventType.ACTION_EXECUTING,
                            "Provider confirms nothing was applied; retrying once",
                            actor=Actor.SYSTEM, action_id=action.id, external_app=action.external_app, status="retrying",
                        )
                        continue
                elif res.error.retryable and attempt < MAX_MUTATION_ATTEMPTS:
                    continue
                self.ledger.resolve(key, "FAILED")
                action = self._update(
                    action.id, execution_status=ExecutionStatus.FAILED.value,
                    verification_status=VerificationStatus.NOT_APPLICABLE.value,
                    error=res.error.model_dump(), completed_at=datetime.now(UTC),
                )
                self.bus.publish(
                    investigation_id, EventType.ACTION_FAILED, f"Action failed: {action.title}",
                    actor=Actor.SYSTEM, action_id=action.id, external_app=action.external_app, status="failed",
                    summary=res.error.message, error_code=res.error.code,
                )
                return action

        if self.lifecycle.status(investigation_id) == InvestigationStatus.EXECUTING:
            self.lifecycle.transition(investigation_id, InvestigationStatus.VERIFYING, reason="Independently verifying the side effect")
        result = await self._verify(ctx, action, marker)
        with self.db.session() as s:
            s.add(
                Verification(
                    id=new_id("ver"), action_id=action.id, method=result.method, result=result.status.value,
                    expected_state=result.expected, observed_state=result.observed, checks=result.checks,
                    confidence=result.confidence, error_code=result.error_code,
                )
            )
        action = self._update(
            action.id, verification_status=result.status.value,
            verification_details={"method": result.method, "checks": result.checks, "observed": result.observed},
            completed_at=datetime.now(UTC),
        )
        passed = sum(c["passed"] for c in result.checks)
        self.bus.publish(
            investigation_id, EventType.VERIFICATION,
            {
                VerificationStatus.VERIFIED: f"Verified: {action.external_result_id} matches the intended change",
                VerificationStatus.FAILED: "Verification failed: provider state does not match the intended change",
                VerificationStatus.UNKNOWN: "Verification inconclusive: provider state could not be re-read",
            }[result.status],
            actor=Actor.SYSTEM, action_id=action.id, external_app=action.external_app, status=result.status.value,
            summary=f"{passed}/{len(result.checks)} checks passed via {result.method}",
            data={"checks": result.checks, "observed": result.observed},
        )
        return action

    @staticmethod
    def _tool_call(action: Action) -> tuple[str, dict]:
        p = action.parameters
        if action.action_type == "create_github_issue":
            return "github.create_issue", {"title": p["title"], "body": p["body"], "labels": p.get("labels", [])}
        if action.action_type == "comment_github_issue":
            return "github.create_comment", {"issue_number": p["issue_number"], "body": p["body"]}
        raise ValueError(f"Unsupported action type {action.action_type}")

    async def _lookup(self, ctx: ToolContext, action: Action, marker: str) -> tuple[dict | None, bool]:
        if action.action_type == "create_github_issue":
            return await find_issue_by_marker(self.runner, ctx, marker)
        return await find_comment_by_marker(self.runner, ctx, action.parameters["issue_number"], marker)

    def _record_success(self, investigation_id: str, action: Action, key: str, data: dict, *, recovered: bool) -> Action:
        if action.action_type == "create_github_issue":
            ext, label = f"{action.target}#{data.get('number')}", f"issue #{data.get('number')}"
        else:
            ext, label = f"{action.target}/comment/{data.get('id')}", f"comment on #{action.parameters.get('issue_number')}"
        self.ledger.resolve(key, "SUCCEEDED", external_result_id=ext, external_url=data.get("url"))
        action = self._update(
            action.id, execution_status=ExecutionStatus.SUCCEEDED.value,
            external_result_id=ext, external_url=data.get("url"), error=None,
        )
        self.bus.publish(
            investigation_id, EventType.ACTION_EXECUTED,
            f"Found {label} created by the earlier request; not retrying (no duplicate)" if recovered else f"Created {label}",
            actor=Actor.TOOL, action_id=action.id, external_app=action.external_app, status="succeeded",
            summary=data.get("url"), data={"external_result_id": ext, "recovered_after_ambiguity": recovered},
        )
        return action

    def _mark_unknown(self, investigation_id: str, action: Action, why: str) -> Action:
        action = self._update(
            action.id, execution_status=ExecutionStatus.UNKNOWN.value,
            verification_status=VerificationStatus.UNKNOWN.value, completed_at=datetime.now(UTC),
        )
        self.bus.publish(
            investigation_id, EventType.ACTION_FAILED, "Action outcome unknown", actor=Actor.SYSTEM,
            action_id=action.id, external_app=action.external_app, status="unknown", summary=why,
        )
        return action

    async def _verify(self, ctx: ToolContext, action: Action, marker: str) -> VerificationResult:
        p = action.parameters
        if action.action_type == "create_github_issue":
            number = int(str(action.external_result_id).rsplit("#", 1)[-1])
            return await verify_issue(
                self.runner, ctx, number=number, repo=action.target, title=p["title"], markers=[marker, *p.get("markers", [])]
            )
        return await verify_comment(self.runner, ctx, issue_number=p["issue_number"], marker=marker)
