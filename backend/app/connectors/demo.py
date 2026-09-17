"""Seeded demo connectors. They return provider-shaped payloads (Google Sheets values API,
GitHub REST, Slack Web API) so the same tool parsing code runs against demo and real data."""

import asyncio
import random
from datetime import datetime

from app.connectors.faults import FaultInjector
from app.errors import ErrorCode, ProviderError
from app.scenarios import DemoWorld, parse_dt


class _DemoClient:
    app = ""

    def __init__(self, world: DemoWorld, faults: FaultInjector, latency_ms: int = 0):
        self.world = world
        self.faults = faults
        self.latency_ms = latency_ms
        self._rng = random.Random(7)

    async def _enter(self, operation: str):
        if self.latency_ms:
            await asyncio.sleep(self.latency_ms / 1000 * self._rng.uniform(0.6, 1.4))
        fault = self.faults.take(self.app, operation)
        if fault and fault.type not in ("malformed", "timeout_after_commit"):
            self.faults.raise_for(fault, self.app, operation)
        return fault


class DemoSheetsClient(_DemoClient):
    app = "sheets"

    @property
    def spreadsheet_id(self) -> str:
        return self.world.sheets.get("spreadsheet_id", "demo-spreadsheet")

    async def get_metadata(self) -> dict:
        await self._enter("get_metadata")
        return {
            "spreadsheetId": self.spreadsheet_id,
            "properties": {"title": self.world.sheets.get("title", "Demo metrics")},
            "sheets": [
                {
                    "properties": {
                        "title": name,
                        "gridProperties": {
                            "rowCount": len(tab.get("rows", [])) + 1,
                            "columnCount": len(tab.get("columns", [])),
                        },
                    }
                }
                for name, tab in self.world.sheets.get("tabs", {}).items()
            ],
        }

    async def get_values(self, tab: str) -> dict:
        fault = await self._enter("get_values")
        if tab not in self.world.sheets.get("tabs", {}):
            raise ProviderError(ErrorCode.NOT_FOUND, f"Sheet tab '{tab}' not found", status_code=404)
        data = self.world.sheets["tabs"][tab]
        if fault and fault.type == "malformed":
            return {"range": f"{tab}!A1:Z", "values": "<html>Service Unavailable</html>"}
        return {
            "range": f"{tab}!A1:Z{len(data['rows']) + 1}",
            "majorDimension": "ROWS",
            "values": [list(data["columns"])] + [list(r) for r in data["rows"]],
        }


class DemoGitHubClient(_DemoClient):
    app = "github"

    @property
    def repo(self) -> str:
        return self.world.github.get("repo", "acme/storefront")

    def _url(self, path: str) -> str:
        return f"https://github.com/{self.repo}/{path}"

    async def list_deployments(self, since: datetime, until: datetime) -> list[dict]:
        await self._enter("list_deployments")
        out = []
        for d in self.world.github["deployments"]:
            created = parse_dt(d["created_at"])
            if since <= created <= until:
                out.append(
                    {
                        "id": d["id"],
                        "sha": d["sha"],
                        "ref": d["ref"],
                        "environment": d.get("environment", "production"),
                        "description": d.get("description", ""),
                        "creator": {"login": d.get("creator", "deploy-bot")},
                        "created_at": created.isoformat().replace("+00:00", "Z"),
                        "url": self._url(f"deployments/{d['id']}"),
                    }
                )
        return sorted(out, key=lambda x: x["created_at"], reverse=True)

    async def list_deployment_commits(self, deployment_id: int) -> list[dict]:
        await self._enter("list_deployment_commits")
        for d in self.world.github["deployments"]:
            if d["id"] == deployment_id:
                return [
                    {
                        "sha": c["sha"],
                        "html_url": self._url(f"commit/{c['sha']}"),
                        "commit": {
                            "message": c["message"],
                            "author": {"name": c.get("author", "dev"), "date": d["created_at"]},
                        },
                        "files": [{"filename": f} for f in c.get("files", [])],
                    }
                    for c in d.get("commits", [])
                ]
        raise ProviderError(ErrorCode.NOT_FOUND, f"Deployment {deployment_id} not found", status_code=404)

    def _issue_payload(self, issue: dict) -> dict:
        return {
            "number": issue["number"],
            "title": issue["title"],
            "body": issue.get("body", ""),
            "state": issue.get("state", "open"),
            "labels": [{"name": n} for n in issue.get("labels", [])],
            "created_at": parse_dt(issue["created_at"]).isoformat().replace("+00:00", "Z"),
            "html_url": self._url(f"issues/{issue['number']}"),
            "user": {"login": issue.get("user", "someone")},
            "repository": self.repo,
        }

    async def list_issues(self, state: str = "all") -> list[dict]:
        await self._enter("list_issues")
        issues = self.world.github["issues"]
        return [
            self._issue_payload(i) for i in issues if state == "all" or i.get("state", "open") == state
        ]

    async def create_issue(self, title: str, body: str, labels: list[str]) -> dict:
        fault = await self._enter("create_issue")
        number = self.world.github["next_issue_number"]
        self.world.github["next_issue_number"] += 1
        issue = {
            "number": number,
            "title": title,
            "body": body,
            "labels": labels,
            "state": "open",
            "created_at": self.world.reference_time.isoformat(),
            "user": "surge-bot",
        }
        self.world.github["issues"].append(issue)
        if fault and fault.type == "timeout_after_commit":
            raise ProviderError(
                ErrorCode.TIMEOUT,
                "github.create_issue timed out waiting for a response (injected fault; the issue may exist)",
                ambiguous=True,
            )
        return self._issue_payload(issue)

    async def get_issue(self, number: int) -> dict:
        await self._enter("get_issue")
        for issue in self.world.github["issues"]:
            if issue["number"] == number:
                return self._issue_payload(issue)
        raise ProviderError(ErrorCode.NOT_FOUND, f"Issue #{number} not found", status_code=404)

    async def create_comment(self, number: int, body: str) -> dict:
        fault = await self._enter("create_comment")
        if not any(i["number"] == number for i in self.world.github["issues"]):
            raise ProviderError(ErrorCode.NOT_FOUND, f"Issue #{number} not found", status_code=404)
        comments = self.world.github["comments"].setdefault(str(number), [])
        comment = {"id": 9000 + sum(len(v) for v in self.world.github["comments"].values()), "body": body}
        comments.append(comment)
        if fault and fault.type == "timeout_after_commit":
            raise ProviderError(
                ErrorCode.TIMEOUT, "github.create_comment timed out (injected fault)", ambiguous=True
            )
        return {**comment, "html_url": self._url(f"issues/{number}#issuecomment-{comment['id']}")}

    async def list_comments(self, number: int) -> list[dict]:
        await self._enter("list_comments")
        return [
            {**c, "html_url": self._url(f"issues/{number}#issuecomment-{c['id']}")}
            for c in self.world.github["comments"].get(str(number), [])
        ]


class DemoSlackClient(_DemoClient):
    app = "slack"

    def _channel(self, channel_id: str) -> dict:
        for c in self.world.slack["channels"]:
            if c["id"] == channel_id:
                return c
        return {"id": channel_id, "name": channel_id}

    async def search_messages(self, terms: list[str], since: datetime, until: datetime, limit: int) -> dict:
        fault = await self._enter("search_messages")
        if fault and fault.type == "malformed":
            return {"ok": True, "messages": {"matches": [{"txt": None, "chan": 12}]}}
        lowered = [t.lower() for t in terms]
        matches = []
        for m in self.world.slack["messages"]:
            ts = parse_dt(m["ts"])
            if not (since <= ts <= until):
                continue
            if lowered and not any(t in m["text"].lower() for t in lowered):
                continue
            channel = self._channel(m["channel"])
            epoch = f"{ts.timestamp():.6f}"
            matches.append(
                {
                    "channel": {"id": channel["id"], "name": channel["name"]},
                    "user": m["user"],
                    "username": m["user"],
                    "text": m["text"],
                    "ts": epoch,
                    "permalink": f"https://acme.slack.com/archives/{channel['id']}/p{epoch.replace('.', '')}",
                }
            )
        matches.sort(key=lambda x: float(x["ts"]))
        return {"ok": True, "messages": {"total": len(matches), "matches": matches[:limit]}}
