from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.api.deps import get_services
from app.api.schemas import ConnectorsOut
from app.auth.deps import get_current_user_optional, require_user
from app.connectors.faults import FAULT_PRESETS
from app.db.models import ANONYMOUS_USER_ID, User
from app.enums import App
from app.services import Services

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


@router.get("", response_model=ConnectorsOut)
async def list_connectors(user: User | None = Depends(get_current_user_optional), services: Services = Depends(get_services)):
    settings = services.settings
    try:
        world = services.worlds.get(f"demo:{settings.demo_scenario}", settings.demo_scenario)
    except (KeyError, FileNotFoundError):
        world = None
    return {
        "default_mode": settings.connector_mode.value,
        "connectors": services.connectors.status(world, user_id=user.id if user else ANONYMOUS_USER_ID),
        "fault_presets": {name: preset["description"] for name, preset in FAULT_PRESETS.items()},
    }


@router.post("/{app}/start")
async def start_oauth(app: App, user: User = Depends(require_user), services: Services = Depends(get_services)) -> dict:
    """Connecting a real account is a signed-in action — the OAuth `state` remembers which user
    is connecting, so the callback (a plain browser redirect, no auth header) can attribute it."""
    return services.oauth.start(app.value, user.id)


@router.get("/{app}/callback", include_in_schema=True)
async def oauth_callback(
    app: App,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    services: Services = Depends(get_services),
):
    await services.oauth.callback(app.value, code, state, error)
    return RedirectResponse(
        f"{services.settings.frontend_url.rstrip('/')}/connectors?connected={app.value}", status_code=303
    )


@router.post("/{app}/disconnect")
async def disconnect(app: App, user: User = Depends(require_user), services: Services = Depends(get_services)) -> dict:
    return {"app": app.value, "disconnected": services.credentials.delete(app.value, user.id)}
