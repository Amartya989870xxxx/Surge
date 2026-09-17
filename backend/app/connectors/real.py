"""Real provider clients. Each exposes the same async surface as its demo counterpart."""

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from urllib.parse import quote

import httpx

from app.connectors.faults import FaultInjector
from app.errors import ErrorCode, ProviderError, classify_http_status
from app.scenarios import parse_dt


class _HTTPClient:
    app = ""

    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def _send(
        self,
        method: str,
        url: str,
        *,
        headers: dict,
        params: dict | None = None,
        json: dict | None = None,
        data: dict | None = None,
    ) -> httpx.Response:
        mutating = method.upper() != "GET"
        try:
            resp = await self.http.request(method, url, headers=headers, params=params, json=json, data=data)
        except httpx.TimeoutException as exc:
            raise ProviderError(
                ErrorCode.TIMEOUT, f"{self.app} request timed out", ambiguous=mutating
            ) from exc
        except httpx.TransportError as exc:
            raise ProviderError(
                ErrorCode.CONNECTOR_UNAVAILABLE, f"{self.app} unreachable ({type(exc).__name__})"
            ) from exc
        if resp.status_code >= 400:
            code = classify_http_status(resp.status_code)
            if resp.status_code == 403 and resp.headers.get("x-ratelimit-remaining") == "0":
                code = ErrorCode.RATE_LIMITED
            raise ProviderError(
                code,
                f"{self.app} returned HTTP {resp.status_code}",
                status_code=resp.status_code,
                ambiguous=mutating and resp.status_code >= 500,
            )
        return resp

    def _json(self, resp: httpx.Response):
        try:
            return resp.json()
        except ValueError as exc:
            raise ProviderError(ErrorCode.MALFORMED_RESPONSE, f"{self.app} returned non-JSON body") from exc


class RealGitHubClient(_HTTPClient):
    app = "github"
    API = "https://api.github.com"

    def __init__(self, http: httpx.AsyncClient, token: str, repo: str):
        super().__init__(http)
        self.repo = repo
        self._token = token
        self._refs: dict[int, str] = {}

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "surge-agent",
        }

    async def _get(self, path: str, params: dict | None = None):
        return self._json(await self._send("GET", f"{self.API}{path}", headers=self._headers, params=params))

    async def list_deployments(self, since: datetime, until: datetime) -> list[dict]:
        out = []
        for d in await self._get(f"/repos/{self.repo}/deployments", {"per_page": 50}):
            created = parse_dt(d["created_at"])
            if since <= created <= until:
                self._refs[d["id"]] = d["sha"]
                out.append(
                    {
                        "id": d["id"],
                        "sha": d["sha"],
                        "ref": d.get("ref") or d["sha"][:7],
                        "environment": d.get("environment"),
                        "description": d.get("description") or "",
                        "creator": d.get("creator") or {},
                        "created_at": d["created_at"],
                        "url": f"https://github.com/{self.repo}/deployments",
                    }
                )
        for r in await self._get(f"/repos/{self.repo}/releases", {"per_page": 30}):
            published = r.get("published_at") or r.get("created_at")
            if not published or not (since <= parse_dt(published) <= until):
                continue
            self._refs[r["id"]] = r["tag_name"]
            out.append(
                {
                    "id": r["id"],
                    "sha": r.get("target_commitish") or "",
                    "ref": r["tag_name"],
                    "environment": "release",
                    "description": r.get("name") or r["tag_name"],
                    "creator": r.get("author") or {},
                    "created_at": published,
                    "url": r.get("html_url"),
                }
            )
        return sorted(out, key=lambda x: x["created_at"], reverse=True)

    async def list_deployment_commits(self, deployment_id: int) -> list[dict]:
        ref = self._refs.get(deployment_id)
        if ref is None:
            ref = (await self._get(f"/repos/{self.repo}/deployments/{deployment_id}"))["sha"]
        return [await self._get(f"/repos/{self.repo}/commits/{quote(ref, safe='')}")]

    async def list_issues(self, state: str = "all") -> list[dict]:
        items = await self._get(f"/repos/{self.repo}/issues", {"state": state, "per_page": 100})
        return [{**i, "repository": self.repo} for i in items if "pull_request" not in i]

    async def create_issue(self, title: str, body: str, labels: list[str]) -> dict:
        resp = await self._send(
            "POST",
            f"{self.API}/repos/{self.repo}/issues",
            headers=self._headers,
            json={"title": title, "body": body, "labels": labels},
        )
        return {**self._json(resp), "repository": self.repo}

    async def get_issue(self, number: int) -> dict:
        return {**(await self._get(f"/repos/{self.repo}/issues/{number}")), "repository": self.repo}

    async def create_comment(self, number: int, body: str) -> dict:
        resp = await self._send(
            "POST",
            f"{self.API}/repos/{self.repo}/issues/{number}/comments",
            headers=self._headers,
            json={"body": body},
        )
        return self._json(resp)

    async def list_comments(self, number: int) -> list[dict]:
        return await self._get(f"/repos/{self.repo}/issues/{number}/comments", {"per_page": 100})


_SLACK_AUTH_ERRORS = {
    "invalid_auth",
    "not_authed",
    "token_revoked",
    "token_expired",
    "account_inactive",
    "missing_scope",
    "not_in_channel",
}


class RealSlackClient(_HTTPClient):
    app = "slack"
    API = "https://slack.com/api"

    def __init__(self, http: httpx.AsyncClient, bot_token: str, user_token: str, channels: list[str]):
        super().__init__(http)
        self._bot = bot_token
        self._user = user_token
        self.channels = channels

    async def _call(self, method: str, token: str, params: dict) -> dict:
        resp = await self._send(
            "GET", f"{self.API}/{method}", headers={"Authorization": f"Bearer {token}"}, params=params
        )
        body = self._json(resp)
        if not body.get("ok"):
            err = body.get("error", "unknown_error")
            if err in _SLACK_AUTH_ERRORS:
                code = ErrorCode.AUTH_FAILED
            elif err == "ratelimited":
                code = ErrorCode.RATE_LIMITED
            else:
                code = ErrorCode.INVALID_REQUEST
            raise ProviderError(code, f"Slack API error: {err}")
        return body

    async def search_messages(self, terms: list[str], since: datetime, until: datetime, limit: int) -> dict:
        found: dict[tuple, dict] = {}
        lo, hi = since.timestamp(), until.timestamp()
        if self._user:
            after = (since - timedelta(days=1)).date().isoformat()
            for term in terms[:6]:
                body = await self._call(
                    "search.messages",
                    self._user,
                    {"query": f"{term} after:{after}", "count": min(limit, 100), "sort": "timestamp"},
                )
                for m in body.get("messages", {}).get("matches", []):
                    channel_id = (m.get("channel") or {}).get("id")
                    if self.channels and channel_id not in self.channels:
                        continue
                    if lo <= float(m.get("ts", 0)) <= hi:
                        found[(channel_id, m.get("ts"))] = m
        elif self._bot and self.channels:
            lowered = [t.lower() for t in terms]
            for channel in self.channels:
                info = await self._call("conversations.info", self._bot, {"channel": channel})
                name = info.get("channel", {}).get("name", channel)
                history = await self._call(
                    "conversations.history",
                    self._bot,
                    {"channel": channel, "oldest": f"{lo:.6f}", "latest": f"{hi:.6f}", "limit": 200},
                )
                for m in history.get("messages", []):
                    text = m.get("text", "")
                    if any(t in text.lower() for t in lowered):
                        found[(channel, m["ts"])] = {
                            "channel": {"id": channel, "name": name},
                            "user": m.get("user"),
                            "username": m.get("user"),
                            "text": text,
                            "ts": m["ts"],
                            "permalink": None,
                        }
        else:
            raise ProviderError(
                ErrorCode.CONNECTOR_UNAVAILABLE,
                "Slack connector needs a user token (search:read) or a bot token plus SURGE_SLACK_CHANNELS",
            )
        ordered = sorted(found.values(), key=lambda m: float(m["ts"]))
        return {"ok": True, "messages": {"total": len(ordered), "matches": ordered[:limit]}}


class RealSheetsClient(_HTTPClient):
    app = "sheets"
    API = "https://sheets.googleapis.com/v4/spreadsheets"

    def __init__(
        self,
        http: httpx.AsyncClient,
        token_provider: Callable[[bool], Awaitable[str]],
        spreadsheet_id: str,
    ):
        super().__init__(http)
        self._token_provider = token_provider
        self.spreadsheet_id = spreadsheet_id

    async def _get(self, url: str, params: dict | None = None):
        token = await self._token_provider(False)
        try:
            resp = await self._send("GET", url, headers={"Authorization": f"Bearer {token}"}, params=params)
        except ProviderError as exc:
            if exc.status_code != 401:
                raise
            token = await self._token_provider(True)
            resp = await self._send("GET", url, headers={"Authorization": f"Bearer {token}"}, params=params)
        return self._json(resp)

    async def get_metadata(self) -> dict:
        return await self._get(
            f"{self.API}/{self.spreadsheet_id}",
            {"fields": "spreadsheetId,properties.title,sheets.properties"},
        )

    async def get_values(self, tab: str) -> dict:
        a1 = quote(f"{tab}!A1:Z5000", safe="")
        return await self._get(f"{self.API}/{self.spreadsheet_id}/values/{a1}")


class FaultProxy:
    """Applies pre-call fault injection to a real client, so the degraded-path demo also works
    with live connectors. Injected failures are always labelled as injected."""

    def __init__(self, client, app: str, faults: FaultInjector):
        self._client = client
        self._app = app
        self._faults = faults

    def __getattr__(self, name: str):
        attr = getattr(self._client, name)
        if name.startswith("_") or not callable(attr):
            return attr

        async def wrapper(*args, **kwargs):
            fault = self._faults.take(self._app, name)
            if fault and fault.type not in ("malformed", "timeout_after_commit"):
                self._faults.raise_for(fault, self._app, name)
            return await attr(*args, **kwargs)

        return wrapper
