import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.connectors.credentials import CredentialStore
from app.db.models import OAuthState
from app.db.session import Database
from app.errors import ErrorCode, SurgeAPIError

STATE_TTL = timedelta(minutes=10)

PROVIDERS = {
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "scope": "repo",
        "client_id": "github_client_id",
        "client_secret": "github_client_secret",
    },
    "slack": {
        "authorize_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "scope": "channels:history,channels:read,chat:write",
        "user_scope": "search:read",
        "client_id": "slack_client_id",
        "client_secret": "slack_client_secret",
    },
    "sheets": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scope": "https://www.googleapis.com/auth/spreadsheets.readonly",
        "client_id": "google_client_id",
        "client_secret": "google_client_secret",
        "extra": {"access_type": "offline", "prompt": "consent", "response_type": "code"},
    },
}


class OAuthService:
    def __init__(self, settings: Settings, db: Database, credentials: CredentialStore, http: httpx.AsyncClient):
        self.settings = settings
        self.db = db
        self.credentials = credentials
        self.http = http

    def _provider(self, app: str) -> dict:
        if app not in PROVIDERS:
            raise SurgeAPIError(ErrorCode.NOT_FOUND, f"Unknown connector '{app}'", http_status=404)
        return PROVIDERS[app]

    def is_configured(self, app: str) -> bool:
        p = PROVIDERS.get(app)
        return bool(p and getattr(self.settings, p["client_id"]) and getattr(self.settings, p["client_secret"]))

    def redirect_uri(self, app: str) -> str:
        return f"{self.settings.public_base_url.rstrip('/')}/api/connectors/{app}/callback"

    def start(self, app: str, user_id: str) -> dict:
        provider = self._provider(app)
        if not self.is_configured(app):
            raise SurgeAPIError(
                ErrorCode.INVALID_STATE,
                f"OAuth for {app} is not configured on the server (missing client id/secret)",
                http_status=409,
            )
        state = secrets.token_urlsafe(32)
        with self.db.session() as s:
            s.add(OAuthState(state=state, app=app, user_id=user_id))
        params = {
            "client_id": getattr(self.settings, provider["client_id"]),
            "redirect_uri": self.redirect_uri(app),
            "scope": provider["scope"],
            "state": state,
            **provider.get("extra", {}),
        }
        if "user_scope" in provider:
            params["user_scope"] = provider["user_scope"]
        return {"authorization_url": f"{provider['authorize_url']}?{urlencode(params)}", "state": state}

    def _consume_state(self, app: str, state: str | None) -> str:
        if not state:
            raise SurgeAPIError(ErrorCode.INVALID_REQUEST, "Missing OAuth state", http_status=400)
        with self.db.session() as s:
            row = s.get(OAuthState, state)
            valid = (
                row is not None
                and row.app == app
                and not row.used
                and datetime.now(UTC) - row.created_at <= STATE_TTL
            )
            user_id = row.user_id if row is not None else None
            if row is not None:
                row.used = True
        if not valid:
            raise SurgeAPIError(ErrorCode.INVALID_REQUEST, "Invalid or expired OAuth state", http_status=400)
        return user_id

    async def callback(self, app: str, code: str | None, state: str | None, error: str | None = None) -> str:
        provider = self._provider(app)
        user_id = self._consume_state(app, state)
        if error or not code:
            raise SurgeAPIError(ErrorCode.AUTH_FAILED, f"Authorization was not granted ({error or 'no code'})")
        data = {
            "client_id": getattr(self.settings, provider["client_id"]),
            "client_secret": getattr(self.settings, provider["client_secret"]),
            "code": code,
            "redirect_uri": self.redirect_uri(app),
        }
        if app == "sheets":
            data["grant_type"] = "authorization_code"
        try:
            resp = await self.http.post(provider["token_url"], data=data, headers={"Accept": "application/json"})
            body = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SurgeAPIError(ErrorCode.CONNECTOR_UNAVAILABLE, f"Token exchange with {app} failed") from exc

        if app == "slack":
            if not body.get("ok"):
                raise SurgeAPIError(ErrorCode.AUTH_FAILED, "Slack token exchange was rejected")
            user_token = (body.get("authed_user") or {}).get("access_token")
            access = user_token or body.get("access_token")
            label = (body.get("team") or {}).get("name")
            self.credentials.save(app, access, user_id=user_id, account_label=label, scopes=body.get("scope"))
            return label or "slack"

        access = body.get("access_token")
        if not access:
            raise SurgeAPIError(ErrorCode.AUTH_FAILED, f"{app} token exchange was rejected")
        expires_at = None
        if body.get("expires_in"):
            expires_at = datetime.now(UTC) + timedelta(seconds=int(body["expires_in"]))
        label = app
        if app == "github":
            try:
                me = await self.http.get(
                    "https://api.github.com/user", headers={"Authorization": f"Bearer {access}"}
                )
                label = me.json().get("login", "github")
            except (httpx.HTTPError, ValueError):
                pass
        self.credentials.save(
            app,
            access,
            user_id=user_id,
            refresh_token=body.get("refresh_token"),
            account_label=label,
            scopes=body.get("scope"),
            expires_at=expires_at,
        )
        return label

    async def google_access_token(self, user_id: str, force_refresh: bool) -> str:
        stored = self.credentials.get("sheets", user_id)
        access = (stored or {}).get("access_token") or self.settings.google_access_token
        refresh = (stored or {}).get("refresh_token") or self.settings.google_refresh_token
        expires_at = (stored or {}).get("expires_at")
        expired = expires_at is not None and expires_at <= datetime.now(UTC) + timedelta(seconds=60)
        if access and not force_refresh and not expired:
            return access
        if not (refresh and self.is_configured("sheets")):
            if access:
                return access
            from app.errors import ProviderError

            raise ProviderError(ErrorCode.AUTH_FAILED, "Google credentials missing or expired")
        resp = await self.http.post(
            PROVIDERS["sheets"]["token_url"],
            data={
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            },
        )
        body = resp.json()
        if "access_token" not in body:
            from app.errors import ProviderError

            raise ProviderError(ErrorCode.AUTH_FAILED, "Google token refresh was rejected")
        self.credentials.save(
            "sheets",
            body["access_token"],
            user_id=user_id,
            refresh_token=refresh,
            account_label=(stored or {}).get("account_label") or "google",
            expires_at=datetime.now(UTC) + timedelta(seconds=int(body.get("expires_in", 3600))),
        )
        return body["access_token"]
