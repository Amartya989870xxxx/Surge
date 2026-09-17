import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import auth, connectors, evaluations, investigations, system
from app.config import Settings, get_settings
from app.errors import ErrorCode, SurgeAPIError
from app.llm.client import StructuredLLM
from app.observability.logging import configure_logging
from app.services import build_services, recover_interrupted_runs

logger = logging.getLogger("surge.api")

DESCRIPTION = """Surge is an evidence-first investigation and response agent.

Create an investigation, subscribe to its Server-Sent Events stream, inspect evidence, hypotheses and
claims, approve the proposed action, and read back the independently verified outcome. Evaluation
endpoints expose reliability metrics computed from real scenario runs."""


class BodySizeLimit:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            for name, value in scope.get("headers", []):
                if name == b"content-length" and value.isdigit() and int(value) > self.max_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content={"error": {"code": "INVALID_REQUEST", "message": "Request body too large", "retryable": False}},
                    )
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)


def create_app(settings: Settings | None = None, llm: StructuredLLM | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        services = build_services(settings, llm=llm)
        app.state.services = services
        recovered = recover_interrupted_runs(services)
        if recovered:
            logger.warning("Marked %d interrupted investigation(s) as failed", recovered)
        yield
        await services.aclose()

    app = FastAPI(title="Surge API", version=settings.version, description=DESCRIPTION, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        allow_credentials=False,
    )
    app.add_middleware(BodySizeLimit, max_bytes=settings.max_request_bytes)

    @app.exception_handler(SurgeAPIError)
    async def _surge_error(_, exc: SurgeAPIError):
        return JSONResponse(status_code=exc.http_status, content=exc.to_dict())

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_, exc: RequestValidationError):
        details = [{"loc": [str(p) for p in e.get("loc", [])], "message": e.get("msg", "")} for e in exc.errors()]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": ErrorCode.INVALID_REQUEST.value,
                    "message": "Request validation failed",
                    "retryable": False,
                    "details": details,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_, exc: StarletteHTTPException):
        code = ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.INVALID_REQUEST
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code.value, "message": str(exc.detail), "retryable": False}},
        )

    @app.exception_handler(Exception)
    async def _unexpected(_, exc: Exception):
        logger.exception("Unhandled API error")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": ErrorCode.INTERNAL.value, "message": "Unexpected server error", "retryable": True}},
        )

    for router in (auth.router, investigations.router, connectors.router, evaluations.router, system.router):
        app.include_router(router)
    return app


app = create_app()
