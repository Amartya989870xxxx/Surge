import asyncio
import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.api import serializers as ser
from app.api.deps import get_services
from app.api.schemas import (
    ActionOut,
    ApproveRequest,
    ClaimOut,
    CreateInvestigationRequest,
    EventOut,
    EvidenceOut,
    HypothesisOut,
    InvestigationCreated,
    InvestigationDetailOut,
    InvestigationListOut,
    RerunRequest,
)
from app.auth.deps import get_current_user_optional
from app.connectors.faults import expand_faults
from app.db.models import (
    ANONYMOUS_USER_ID,
    Action,
    Claim,
    EvidenceItem,
    EvidenceLink,
    Hypothesis,
    Investigation,
    InvestigationEvent,
    User,
    Verification,
)
from app.enums import TERMINAL_STATUSES, EventType, ExecutionMode, InvestigationStatus
from app.errors import ErrorCode, SurgeAPIError
from app.services import Services

router = APIRouter(prefix="/api/investigations", tags=["investigations"])

_TERMINAL_EVENTS = {EventType.COMPLETED.value, EventType.FAILED.value, EventType.CANCELLED.value}


def _load(services: Services, investigation_id: str, user: User | None = None) -> Investigation:
    with services.db.session() as s:
        inv = s.get(Investigation, investigation_id)
        if inv is None:
            raise SurgeAPIError(ErrorCode.NOT_FOUND, "Investigation not found", http_status=404)
        s.expunge(inv)
    # Ownership check applies only when the investigation belongs to a real, authenticated user
    # (a row in `users`). The pre-auth "session_id" convenience - an arbitrary client-supplied
    # string with no real credential behind it - keeps its original open-by-ID behavior; it was
    # never a security boundary. A real user's data is only visible to that same authenticated
    # user. 404, not 403, so a non-owner can't even confirm the ID exists (avoids enumeration).
    owner = services.users.get(inv.session_id)
    if owner is not None and (user is None or user.id != owner.id):
        raise SurgeAPIError(ErrorCode.NOT_FOUND, "Investigation not found", http_status=404)
    return inv


async def _aload(services: Services, investigation_id: str, user: User | None = None) -> Investigation:
    """Async twin of _load(), for endpoints migrated to AsyncSession. Same ownership rule."""
    async with services.db.async_session() as s:
        inv = await s.get(Investigation, investigation_id)
        if inv is None:
            raise SurgeAPIError(ErrorCode.NOT_FOUND, "Investigation not found", http_status=404)
        s.expunge(inv)
    owner = await services.users.aget(inv.session_id)
    if owner is not None and (user is None or user.id != owner.id):
        raise SurgeAPIError(ErrorCode.NOT_FOUND, "Investigation not found", http_status=404)
    return inv


async def _aactions(services: Services, investigation_ids: list[str]) -> dict[str, list[Action]]:
    """Async twin of _actions()."""
    out: dict[str, list[Action]] = {i: [] for i in investigation_ids}
    if not investigation_ids:
        return out
    async with services.db.async_session() as s:
        result = await s.scalars(
            select(Action).where(Action.investigation_id.in_(investigation_ids)).order_by(Action.created_at)
        )
        for a in result.all():
            s.expunge(a)
            out[a.investigation_id].append(a)
    return out


def _actions(services: Services, investigation_ids: list[str]) -> dict[str, list[Action]]:
    out: dict[str, list[Action]] = {i: [] for i in investigation_ids}
    if not investigation_ids:
        return out
    with services.db.session() as s:
        for a in s.scalars(
            select(Action).where(Action.investigation_id.in_(investigation_ids)).order_by(Action.created_at)
        ).all():
            s.expunge(a)
            out[a.investigation_id].append(a)
    return out


@router.post("", status_code=202, response_model=InvestigationCreated)
async def create_investigation(
    body: CreateInvestigationRequest,
    user: User | None = Depends(get_current_user_optional),
    services: Services = Depends(get_services),
):
    try:
        faults = expand_faults(body.inject_failures, None)
    except ValueError as exc:
        raise SurgeAPIError(ErrorCode.INVALID_REQUEST, str(exc), http_status=422) from exc
    inv_id = services.orchestrator.create_investigation(
        request=body.request,
        time_range=body.time_range,
        connector_mode=body.connector_mode,
        disabled_apps=body.disabled_apps,
        scenario_id=body.scenario_id,
        faults=faults,
        approval_mode=body.approval_mode,
        reasoning=body.reasoning,
        session_id=user.id if user else body.session_id,
        persona=body.persona or (user.persona if user else None),
    )
    services.runtime.spawn(inv_id, services.orchestrator.run(inv_id))
    inv = _load(services, inv_id, user)
    return {
        "id": inv.id,
        "status": inv.status,
        "stream_url": f"/api/investigations/{inv.id}/stream",
        "connector_mode": inv.connector_mode,
        "reasoning_mode": inv.reasoning_mode,
        "scenario_id": inv.scenario_id,
        "injected_faults": inv.fault_injection or [],
    }


@router.get("", response_model=InvestigationListOut)
async def list_investigations(
    status: str | None = Query(default=None, description="Comma-separated statuses"),
    session_id: str | None = Query(default=None, description="Only investigations created with this session_id"),
    include_evaluation: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    user: User | None = Depends(get_current_user_optional),
    services: Services = Depends(get_services),
):
    # Anonymous callers only ever see the shared "anonymous" bucket (today's demo-mode behavior,
    # unchanged) — never an unfiltered view across every signed-in user's investigations.
    effective_session = session_id or (user.id if user else ANONYMOUS_USER_ID)
    query = select(Investigation)
    count_query = select(func.count()).select_from(Investigation)
    if status:
        wanted = [x.strip().upper() for x in status.split(",") if x.strip()]
        query = query.where(Investigation.status.in_(wanted))
        count_query = count_query.where(Investigation.status.in_(wanted))
    if effective_session:
        query = query.where(Investigation.session_id == effective_session)
        count_query = count_query.where(Investigation.session_id == effective_session)
    if not include_evaluation:
        query = query.where(Investigation.execution_mode != ExecutionMode.EVALUATION.value)
        count_query = count_query.where(Investigation.execution_mode != ExecutionMode.EVALUATION.value)
    with services.db.session() as s:
        rows = s.scalars(query.order_by(Investigation.created_at.desc()).limit(limit)).all()
        total = s.scalar(count_query) or 0
        for r in rows:
            s.expunge(r)
    actions = _actions(services, [r.id for r in rows])
    return {"items": [ser.investigation_summary(r, actions[r.id]) for r in rows], "total": total}


@router.get("/{investigation_id}", response_model=InvestigationDetailOut)
async def get_investigation(
    investigation_id: str,
    user: User | None = Depends(get_current_user_optional),
    services: Services = Depends(get_services),
):
    inv = await _aload(services, investigation_id, user)
    async with services.db.async_session() as s:
        counts = {
            "events": (await s.scalar(select(func.count()).where(InvestigationEvent.investigation_id == inv.id))) or 0,
            "evidence": (await s.scalar(select(func.count()).where(EvidenceItem.investigation_id == inv.id))) or 0,
            "hypotheses": (await s.scalar(select(func.count()).where(Hypothesis.investigation_id == inv.id))) or 0,
            "claims": (await s.scalar(select(func.count()).where(Claim.investigation_id == inv.id))) or 0,
        }
    try:
        connectors = services.runtime.connectors_for(inv).public()
    except KeyError:
        connectors = [{"app": app, "mode": mode} for app, mode in (inv.connector_profile or {}).get("apps", {}).items()]
    actions = await _aactions(services, [inv.id])
    return ser.investigation_detail(inv, actions[inv.id], connectors, counts)


@router.get("/{investigation_id}/events", response_model=list[EventOut])
async def get_events(
    investigation_id: str,
    after: int = Query(default=0, ge=0),
    user: User | None = Depends(get_current_user_optional),
    services: Services = Depends(get_services),
):
    _load(services, investigation_id, user)
    return services.bus.history(investigation_id, after)


@router.get("/{investigation_id}/evidence", response_model=list[EvidenceOut])
async def get_evidence(
    investigation_id: str,
    user: User | None = Depends(get_current_user_optional),
    services: Services = Depends(get_services),
):
    _load(services, investigation_id, user)
    with services.db.session() as s:
        evidence = s.scalars(
            select(EvidenceItem)
            .where(EvidenceItem.investigation_id == investigation_id)
            .order_by(EvidenceItem.relevance_score.desc())
        ).all()
        links = s.scalars(select(EvidenceLink).where(EvidenceLink.investigation_id == investigation_id)).all()
        hyps = {h.id: h for h in s.scalars(select(Hypothesis).where(Hypothesis.investigation_id == investigation_id)).all()}
        return [ser.evidence_item(e, [l for l in links if l.evidence_id == e.id], hyps) for e in evidence]


@router.get("/{investigation_id}/hypotheses", response_model=list[HypothesisOut])
async def get_hypotheses(
    investigation_id: str,
    user: User | None = Depends(get_current_user_optional),
    services: Services = Depends(get_services),
):
    _load(services, investigation_id, user)
    with services.db.session() as s:
        hyps = s.scalars(select(Hypothesis).where(Hypothesis.investigation_id == investigation_id)).all()
        links = s.scalars(select(EvidenceLink).where(EvidenceLink.investigation_id == investigation_id)).all()
        evidence = {e.id: e for e in s.scalars(select(EvidenceItem).where(EvidenceItem.investigation_id == investigation_id)).all()}
        return ser.hypotheses_list(list(hyps), list(links), evidence)


@router.get("/{investigation_id}/actions", response_model=list[ActionOut])
async def get_actions(
    investigation_id: str,
    user: User | None = Depends(get_current_user_optional),
    services: Services = Depends(get_services),
):
    _load(services, investigation_id, user)
    actions = _actions(services, [investigation_id])[investigation_id]
    with services.db.session() as s:
        verifications = s.scalars(select(Verification).where(Verification.action_id.in_([a.id for a in actions]))).all()
        return [ser.action_item(a, [v for v in verifications if v.action_id == a.id]) for a in actions]


@router.get("/{investigation_id}/claims", response_model=list[ClaimOut])
async def get_claims(
    investigation_id: str,
    user: User | None = Depends(get_current_user_optional),
    services: Services = Depends(get_services),
):
    _load(services, investigation_id, user)
    with services.db.session() as s:
        claims = s.scalars(
            select(Claim).where(Claim.investigation_id == investigation_id).order_by(Claim.position)
        ).all()
        return [ser.claim_item(c) for c in claims]


@router.post("/{investigation_id}/approve", response_model=ActionOut)
async def approve_action(
    investigation_id: str,
    body: ApproveRequest,
    user: User | None = Depends(get_current_user_optional),
    services: Services = Depends(get_services),
):
    _load(services, investigation_id, user)  # ownership check before allowing a mutation
    await services.orchestrator.decide_action(
        investigation_id, body.action_id, body.approved, decided_by=body.decided_by, comment=body.comment
    )
    with services.db.session() as s:
        action = s.get(Action, body.action_id)
        verifications = s.scalars(select(Verification).where(Verification.action_id == action.id)).all()
        return ser.action_item(action, list(verifications))


@router.post("/{investigation_id}/cancel")
async def cancel_investigation(
    investigation_id: str,
    user: User | None = Depends(get_current_user_optional),
    services: Services = Depends(get_services),
) -> dict:
    _load(services, investigation_id, user)
    status = await services.orchestrator.cancel(investigation_id)
    return {"id": investigation_id, "status": status}


@router.post("/{investigation_id}/rerun", status_code=202, response_model=InvestigationCreated)
async def rerun_investigation(
    investigation_id: str,
    body: RerunRequest | None = None,
    user: User | None = Depends(get_current_user_optional),
    services: Services = Depends(get_services),
):
    _load(services, investigation_id, user)
    new_id = services.orchestrator.rerun(investigation_id, clear_faults=(body or RerunRequest()).clear_faults)
    services.runtime.spawn(new_id, services.orchestrator.run(new_id))
    inv = _load(services, new_id, user)
    return {
        "id": inv.id,
        "status": inv.status,
        "stream_url": f"/api/investigations/{inv.id}/stream",
        "connector_mode": inv.connector_mode,
        "reasoning_mode": inv.reasoning_mode,
        "scenario_id": inv.scenario_id,
        "injected_faults": inv.fault_injection or [],
    }


def _sse(event: dict) -> str:
    return f"id: {event['sequence']}\nevent: {event['event_type']}\ndata: {json.dumps(event, default=str)}\n\n"


@router.get(
    "/{investigation_id}/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}, "description": "Server-Sent Events of EventOut objects"}},
)
async def stream_events(
    investigation_id: str,
    request: Request,
    after: int = Query(default=0, ge=0),
    user: User | None = Depends(get_current_user_optional),
    services: Services = Depends(get_services),
):
    _load(services, investigation_id, user)
    last_event_id = request.headers.get("last-event-id")
    start = int(last_event_id) if last_event_id and last_event_id.isdigit() else after

    def finished() -> bool:
        status = services.lifecycle.status(investigation_id)
        return status in TERMINAL_STATUSES and not services.runtime.is_running(investigation_id)

    async def generate():
        queue = services.bus.subscribe(investigation_id)
        sent = start
        try:
            yield "retry: 3000\n\n"
            for event in services.bus.history(investigation_id, start):
                yield _sse(event)
                sent = event["sequence"]
            if finished():
                yield "event: end\ndata: {}\n\n"
                return
            while True:
                if await request.is_disconnected():
                    return
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    if finished():
                        yield "event: end\ndata: {}\n\n"
                        return
                    yield ": keep-alive\n\n"
                    continue
                if event["sequence"] <= sent:
                    continue
                yield _sse(event)
                sent = event["sequence"]
                if event["event_type"] in _TERMINAL_EVENTS and event.get("status") != InvestigationStatus.AWAITING_APPROVAL.value:
                    yield "event: end\ndata: {}\n\n"
                    return
        finally:
            services.bus.unsubscribe(investigation_id, queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
