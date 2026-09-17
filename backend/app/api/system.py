from fastapi import APIRouter, Depends

from app.agent.hypotheses import (
    CATALOG,
    MIN_INDEPENDENT_SOURCES,
    MIN_MARGIN,
    STOP_THRESHOLD,
    SUPPORTED_THRESHOLD,
)
from app.agent.policy import ACTION_RISK
from app.agent.probes import PROBES
from app.api.deps import get_services
from app.connectors.faults import FAULT_PRESETS
from app.enums import ApprovalStatus, EventType, ExecutionStatus, InvestigationStatus, VerificationStatus
from app.services import Services

router = APIRouter(tags=["system"])


@router.get("/api/health")
async def health(services: Services = Depends(get_services)) -> dict:
    return {"status": "ok", "version": services.settings.version}


@router.get("/api/system")
async def system(services: Services = Depends(get_services)) -> dict:
    settings = services.settings
    return {
        "name": "Surge",
        "version": settings.version,
        "reasoning": {
            "default_mode": settings.resolved_reasoning_mode().value,
            "llm_available": services.llm.available,
            "active_model": services.llm.model if services.llm.available else None,
            "router": services.llm.status() if hasattr(services.llm, "status") else None,
        },
        "connectors": {
            "default_mode": settings.connector_mode.value,
            "demo_scenario": settings.demo_scenario,
            "demo_simulated_latency_ms": settings.demo_latency_ms,
        },
        "policy": {
            "default_approval": "required",
            "action_risk": {k: v.value for k, v in ACTION_RISK.items()},
            "diagnosis": {
                "supported_threshold": SUPPORTED_THRESHOLD,
                "stop_threshold": STOP_THRESHOLD,
                "min_independent_sources": MIN_INDEPENDENT_SOURCES,
                "min_margin_over_runner_up": MIN_MARGIN,
            },
            "max_tool_calls": settings.max_tool_calls,
        },
        "hypothesis_catalog": [{"kind": t.kind, "label": t.label, "statement": t.statement} for t in CATALOG.values()],
        "probes": [
            {"id": p.id, "app": p.app.value, "title": p.title, "purpose": p.purpose, "discriminates": p.discriminates}
            for p in PROBES.values()
        ],
        "fault_presets": {k: v["description"] for k, v in FAULT_PRESETS.items()},
        "enums": {
            "investigation_status": [s.value for s in InvestigationStatus],
            "event_type": [e.value for e in EventType],
            "approval_status": [s.value for s in ApprovalStatus],
            "execution_status": [s.value for s in ExecutionStatus],
            "verification_status": [s.value for s in VerificationStatus],
        },
    }


@router.get("/api/llm/status")
async def llm_status(services: Services = Depends(get_services)) -> dict:
    status = services.llm.status() if hasattr(services.llm, "status") else {"configured_providers": [], "models": []}
    return {"available": services.llm.available, **status}


@router.get("/api/tools")
async def tools(services: Services = Depends(get_services)) -> list[dict]:
    return services.registry.describe()


@router.get("/api/demo/scenarios")
async def demo_scenarios(services: Services = Depends(get_services)) -> list[dict]:
    return [scenario.public_view() for scenario in services.library.list()]


@router.post("/api/demo/reset")
async def reset_demo(services: Services = Depends(get_services)) -> dict:
    services.worlds.reset()
    return {"reset": True, "detail": "Seeded demo worlds will be rebuilt from their definitions on next use"}
