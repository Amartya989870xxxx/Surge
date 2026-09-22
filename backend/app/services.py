from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import select

from app.actions.executor import ActionExecutor
from app.actions.idempotency import IdempotencyLedger
from app.agent.hypotheses import HypothesisEngine
from app.agent.orchestrator import Orchestrator
from app.agent.planner import Planner
from app.agent.state import Lifecycle
from app.agent.synthesizer import Synthesizer
from app.auth.firebase import FirebaseVerifier
from app.auth.store import UserStore
from app.config import Settings
from app.connectors.credentials import CredentialStore
from app.connectors.manager import ConnectorManager
from app.connectors.oauth import OAuthService
from app.db.models import EvaluationSuite, Investigation
from app.db.session import Database
from app.enums import Actor, EventType, InvestigationStatus
from app.evaluation.runner import EvaluationRunner
from app.evidence.store import EvidenceStore
from app.llm.client import LLMResult, StructuredLLM
from app.llm.router import HybridLLMRouter
from app.observability.events import EventBus
from app.runtime import Runtime
from app.scenarios import ScenarioLibrary, WorldRegistry
from app.tools.registry import ToolRegistry, build_registry
from app.tools.runner import ToolRunner


@dataclass
class Services:
    settings: Settings
    db: Database
    http: httpx.AsyncClient
    bus: EventBus
    registry: ToolRegistry
    runner: ToolRunner
    credentials: CredentialStore
    oauth: OAuthService
    connectors: ConnectorManager
    library: ScenarioLibrary
    worlds: WorldRegistry
    llm: StructuredLLM
    firebase: FirebaseVerifier
    users: UserStore
    evidence: EvidenceStore
    engine: HypothesisEngine
    planner: Planner
    synthesizer: Synthesizer
    lifecycle: Lifecycle
    ledger: IdempotencyLedger
    executor: ActionExecutor
    runtime: Runtime
    orchestrator: Any = None
    evaluations: Any = None

    async def aclose(self) -> None:
        await self.runtime.shutdown()
        await self.http.aclose()
        await self.db.aclose()


def build_services(settings: Settings, llm: StructuredLLM | None = None) -> Services:
    db = Database(settings.database_url)
    db.create_all()
    http = httpx.AsyncClient(timeout=httpx.Timeout(settings.tool_timeout_s, connect=5.0))
    bus = EventBus(db)
    registry = build_registry()
    runner = ToolRunner(registry, bus, settings)
    credentials = CredentialStore(db, settings.secret_key)
    oauth = OAuthService(settings, db, credentials, http)
    connectors = ConnectorManager(settings, credentials, oauth, http)
    library = ScenarioLibrary(settings.scenarios_dir, settings.worlds_dir)
    worlds = WorldRegistry(library)
    firebase = FirebaseVerifier(settings.firebase_project_id, http)
    users = UserStore(db)
    llm = llm or HybridLLMRouter(settings, http)
    if hasattr(llm, "set_observer"):
        llm.set_observer(_routing_observer(bus))
    engine = HypothesisEngine(db)
    lifecycle = Lifecycle(db, bus)
    ledger = IdempotencyLedger(db)
    services = Services(
        settings=settings,
        db=db,
        http=http,
        bus=bus,
        registry=registry,
        runner=runner,
        credentials=credentials,
        oauth=oauth,
        connectors=connectors,
        library=library,
        worlds=worlds,
        firebase=firebase,
        users=users,
        llm=llm,
        evidence=EvidenceStore(db),
        engine=engine,
        planner=Planner(llm),
        synthesizer=Synthesizer(db, engine, llm),
        lifecycle=lifecycle,
        ledger=ledger,
        executor=ActionExecutor(db, bus, runner, ledger, lifecycle),
        runtime=Runtime(connectors, worlds),
    )
    services.orchestrator = Orchestrator(services)
    services.evaluations = EvaluationRunner(services)
    return services


_COMPONENTS = {"plan_next_step": "planner", "assess_evidence": "assessor", "synthesize": "synthesizer"}


def _routing_observer(bus: EventBus):
    """Emits a timeline event whenever reasoning moved to a different model for an investigation:
    a fresh failure on the way, or a change of serving model (including recovery back to primary)."""
    last_route: dict[str, str] = {}

    def observe(trace_id: str | None, purpose: str, result: LLMResult) -> None:
        if not trace_id:
            return
        fresh_failures = [a for a in result.attempts if a["outcome"] not in ("cooling_down", "exhausted")]
        previous = last_route.get(trace_id)
        last_route[trace_id] = result.route
        if not fresh_failures and (previous is None or previous == result.route):
            return
        component = _COMPONENTS.get(purpose, purpose)
        if result.attempts:
            skipped = "; ".join(f"{a['model']} {a['outcome'].replace('_', ' ')}" for a in result.attempts)
            summary = f"{skipped}. The {component} continued on {result.route}."
        else:
            summary = f"{result.route} is available again; the {component} is back on it."
        bus.publish(
            trace_id,
            EventType.LLM_FALLBACK,
            f"Reasoning rerouted to {result.route}",
            actor=Actor.SYSTEM,
            summary=summary,
            data={"component": component, "fallback_to": "model", "served_by": result.route, "attempts": result.attempts},
        )

    return observe


def recover_interrupted_runs(services: Services) -> int:
    """Runs cannot resume mid-loop after a restart; mark them failed but keep everything recorded.
    Runs waiting for approval stay resumable because execution only needs persisted state."""
    active = [
        InvestigationStatus.CREATED,
        InvestigationStatus.PLANNING,
        InvestigationStatus.INVESTIGATING,
        InvestigationStatus.SYNTHESIZING,
        InvestigationStatus.EXECUTING,
        InvestigationStatus.VERIFYING,
    ]
    with services.db.session() as s:
        ids = s.scalars(select(Investigation.id).where(Investigation.status.in_([a.value for a in active]))).all()
        for suite in s.scalars(select(EvaluationSuite).where(EvaluationSuite.status == "running")).all():
            suite.status = "failed"
            suite.error = {"code": "SERVER_RESTART", "message": "The server restarted while this suite was running"}
    for inv_id in ids:
        services.lifecycle.transition(
            inv_id,
            InvestigationStatus.FAILED,
            reason="The server restarted while this run was in progress; state up to that point is preserved",
            error={"code": "SERVER_RESTART"},
        )
        services.bus.publish(
            inv_id, EventType.FAILED, "Investigation interrupted by a server restart",
            actor=Actor.SYSTEM, status=InvestigationStatus.FAILED.value,
        )
    return len(ids)
