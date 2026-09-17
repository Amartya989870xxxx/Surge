from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api import serializers as ser
from app.api.deps import get_services
from app.api.schemas import EvaluationSuiteOut, EvaluationSuiteSummaryOut, RunEvaluationRequest
from app.db.models import EvaluationRun, EvaluationSuite
from app.errors import ErrorCode, SurgeAPIError
from app.services import Services

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


def _detail(services: Services, suite: EvaluationSuite) -> dict:
    with services.db.session() as s:
        runs = s.scalars(select(EvaluationRun).where(EvaluationRun.suite_id == suite.id).order_by(EvaluationRun.timestamp)).all()
        return {
            **ser.suite_summary(suite),
            "report": suite.report,
            "report_text": suite.report_text,
            "error": suite.error,
            "runs": [ser.run_item(r) for r in runs],
        }


@router.post("/run", status_code=202)
async def run_evaluation(body: RunEvaluationRequest | None = None, services: Services = Depends(get_services)) -> dict:
    body = body or RunEvaluationRequest()
    if services.runtime.running_keys("eval:"):
        raise SurgeAPIError(ErrorCode.INVALID_STATE, "An evaluation suite is already running", http_status=409)
    suite_id = services.evaluations.create_suite(body.reasoning, body.scenario_ids)
    services.runtime.spawn(f"eval:{suite_id}", services.evaluations.run_suite(suite_id))
    return {"id": suite_id, "status": "running", "report_url": f"/api/evaluations/{suite_id}"}


@router.get("", response_model=list[EvaluationSuiteSummaryOut])
async def list_evaluations(services: Services = Depends(get_services)):
    with services.db.session() as s:
        suites = s.scalars(select(EvaluationSuite).order_by(EvaluationSuite.started_at.desc()).limit(50)).all()
        return [ser.suite_summary(x) for x in suites]


@router.get("/scenarios")
async def list_scenarios(services: Services = Depends(get_services)) -> list[dict]:
    return [scenario.public_view() for scenario in services.library.list()]


@router.get("/latest", response_model=EvaluationSuiteOut)
async def latest_evaluation(services: Services = Depends(get_services)):
    with services.db.session() as s:
        suite = s.scalar(
            select(EvaluationSuite)
            .where(EvaluationSuite.status == "completed")
            .order_by(EvaluationSuite.completed_at.desc())
            .limit(1)
        )
        if suite is None:
            raise SurgeAPIError(ErrorCode.NOT_FOUND, "No completed evaluation suite yet", http_status=404)
        s.expunge(suite)
    return _detail(services, suite)


@router.get("/{suite_id}", response_model=EvaluationSuiteOut)
async def get_evaluation(suite_id: str, services: Services = Depends(get_services)):
    with services.db.session() as s:
        suite = s.get(EvaluationSuite, suite_id)
        if suite is None:
            raise SurgeAPIError(ErrorCode.NOT_FOUND, "Evaluation suite not found", http_status=404)
        s.expunge(suite)
    return _detail(services, suite)
