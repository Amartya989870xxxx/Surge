import functools
from dataclasses import dataclass, field

import httpx

from app.config import Settings
from app.connectors.credentials import CredentialStore
from app.connectors.demo import DemoGitHubClient, DemoSheetsClient, DemoSlackClient
from app.connectors.faults import FaultInjector
from app.connectors.oauth import OAuthService
from app.connectors.real import FaultProxy, RealGitHubClient, RealSheetsClient, RealSlackClient
from app.db.models import ANONYMOUS_USER_ID
from app.enums import App, ConnectorMode
from app.errors import ErrorCode, ProviderError
from app.scenarios import DemoWorld

DISPLAY_NAMES = {App.SHEETS: "Google Sheets", App.GITHUB: "GitHub", App.SLACK: "Slack"}
CAPABILITIES = {
    App.SHEETS: ["read_metadata", "read_rows"],
    App.GITHUB: ["read_deployments", "read_commits", "read_issues", "create_issue", "comment_issue"],
    App.SLACK: ["search_messages"],
}
_DEMO_CLIENTS = {App.SHEETS: DemoSheetsClient, App.GITHUB: DemoGitHubClient, App.SLACK: DemoSlackClient}


@dataclass
class ConnectorHandle:
    app: App
    mode: ConnectorMode
    client: object | None
    status: str
    account_label: str | None = None
    detail: str | None = None
    simulated_latency_ms: int | None = None

    def public(self) -> dict:
        return {
            "app": self.app.value,
            "display_name": DISPLAY_NAMES[self.app],
            "mode": self.mode.value,
            "status": self.status,
            "account_label": self.account_label,
            "capabilities": CAPABILITIES[self.app] if self.status in ("connected", "demo") else [],
            "detail": self.detail,
            "simulated_latency_ms": self.simulated_latency_ms,
        }


@dataclass
class ConnectorSet:
    handles: dict[App, ConnectorHandle]
    faults: FaultInjector = field(default_factory=FaultInjector)
    world: DemoWorld | None = None

    def mode(self, app: App | str) -> ConnectorMode:
        return self.handles[App(app)].mode

    def client(self, app: App | str):
        handle = self.handles[App(app)]
        if handle.mode == ConnectorMode.DISABLED:
            raise ProviderError(ErrorCode.CONNECTOR_DISABLED, f"{DISPLAY_NAMES[handle.app]} connector is disabled")
        if handle.client is None:
            raise ProviderError(
                ErrorCode.CONNECTOR_UNAVAILABLE,
                handle.detail or f"{DISPLAY_NAMES[handle.app]} connector is not configured",
            )
        return handle.client

    def enabled_apps(self) -> list[App]:
        return [a for a, h in self.handles.items() if h.mode != ConnectorMode.DISABLED]

    def public(self) -> list[dict]:
        return [h.public() for h in self.handles.values()]


class ConnectorManager:
    def __init__(
        self,
        settings: Settings,
        credentials: CredentialStore,
        oauth: OAuthService,
        http: httpx.AsyncClient,
    ):
        self.settings = settings
        self.credentials = credentials
        self.oauth = oauth
        self.http = http

    def default_profile(self, requested: ConnectorMode | None = None, disabled: list[str] | None = None) -> dict:
        profile = {}
        for app in App:
            mode = requested or self.settings.mode_for(app)
            if app.value in (disabled or []):
                mode = ConnectorMode.DISABLED
            profile[app.value] = mode.value
        return profile

    def build(
        self,
        profile: dict,
        *,
        world: DemoWorld | None,
        faults: list[dict] | None = None,
        latency_ms: int = 0,
        user_id: str = ANONYMOUS_USER_ID,
    ) -> ConnectorSet:
        injector = FaultInjector(faults)
        handles: dict[App, ConnectorHandle] = {}
        for app in App:
            mode = ConnectorMode(profile.get(app.value, ConnectorMode.DISABLED))
            if mode == ConnectorMode.DISABLED:
                handles[app] = ConnectorHandle(app, mode, None, "disabled", detail="Disabled for this investigation")
            elif mode == ConnectorMode.DEMO:
                if world is None:
                    handles[app] = ConnectorHandle(app, mode, None, "not_configured", detail="No demo world loaded")
                    continue
                handles[app] = ConnectorHandle(
                    app,
                    mode,
                    _DEMO_CLIENTS[app](world, injector, latency_ms),
                    "demo",
                    account_label=f"Seeded demo world: {world.meta.get('title', world.world_id)}",
                    detail="Deterministic seeded data. Not a live provider.",
                    simulated_latency_ms=latency_ms,
                )
            else:
                handles[app] = self._real_handle(app, injector, user_id)
        return ConnectorSet(handles=handles, faults=injector, world=world)

    def _real_handle(self, app: App, injector: FaultInjector, user_id: str) -> ConnectorHandle:
        s = self.settings
        stored = self.credentials.get(app.value, user_id) or {}
        if app == App.GITHUB:
            token = stored.get("access_token") or (s.github_token if user_id == ANONYMOUS_USER_ID else None)
            if not (token and s.github_repo):
                return ConnectorHandle(
                    app, ConnectorMode.REAL, None, "not_configured",
                    detail="Connect your GitHub account, plus SURGE_GITHUB_REPO must be set on the server",
                )
            client = RealGitHubClient(self.http, token, s.github_repo)
            label = f"{stored.get('account_label') or 'token'} · {s.github_repo}"
        elif app == App.SLACK:
            stored_token = stored.get("access_token") or ""
            user_token = stored_token if stored_token.startswith("xoxp-") else ""
            bot_token = stored_token if not user_token else ""
            if user_id == ANONYMOUS_USER_ID:
                user_token = user_token or s.slack_user_token
                bot_token = bot_token or s.slack_bot_token
            if not (user_token or (bot_token and s.slack_channel_list)):
                return ConnectorHandle(
                    app, ConnectorMode.REAL, None, "not_configured",
                    detail="Connect your Slack account (needs search:read), or configure a bot token plus SURGE_SLACK_CHANNELS",
                )
            client = RealSlackClient(self.http, bot_token, user_token, s.slack_channel_list)
            label = stored.get("account_label") or "slack workspace"
        else:
            has_token = stored.get("access_token") or (
                (s.google_access_token or s.google_refresh_token) if user_id == ANONYMOUS_USER_ID else None
            )
            if not (has_token and s.sheets_spreadsheet_id):
                return ConnectorHandle(
                    app, ConnectorMode.REAL, None, "not_configured",
                    detail="Connect your Google account, plus SURGE_SHEETS_SPREADSHEET_ID must be set on the server",
                )
            token_provider = functools.partial(self.oauth.google_access_token, user_id)
            client = RealSheetsClient(self.http, token_provider, s.sheets_spreadsheet_id)
            label = f"{stored.get('account_label') or 'google'} · {s.sheets_spreadsheet_id[:12]}…"
        return ConnectorHandle(
            app, ConnectorMode.REAL, FaultProxy(client, app.value, injector), "connected", account_label=label
        )

    def status(self, world: DemoWorld | None, user_id: str = ANONYMOUS_USER_ID) -> list[dict]:
        built = self.build(self.default_profile(), world=world, latency_ms=self.settings.demo_latency_ms, user_id=user_id)
        out = []
        for item in built.public():
            item["oauth_configured"] = self.oauth.is_configured(item["app"])
            item["connect_endpoint"] = f"/api/connectors/{item['app']}/start"
            out.append(item)
        return out
