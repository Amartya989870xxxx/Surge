from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.enums import App, RiskLevel
from app.errors import ErrorCode, ProviderError
from app.tools.base import ToolAccess, ToolSpec


class ListDeploymentsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    since: datetime
    until: datetime

    @model_validator(mode="after")
    def _window(self):
        if self.until <= self.since:
            raise ValueError("until must be after since")
        if self.until - self.since > timedelta(days=14):
            raise ValueError("window may not exceed 14 days")
        return self


class DeploymentChangesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deployment_id: int = Field(ge=1)


class ListIssuesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["open", "closed", "all"] = "all"


class IssueNumberArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    number: int = Field(ge=1)


class CreateIssueArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=256)
    body: str = Field(min_length=1, max_length=60000)
    labels: list[str] = Field(default_factory=list, max_length=10)


class CreateCommentArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issue_number: int = Field(ge=1)
    body: str = Field(min_length=1, max_length=60000)


class _Deployment(BaseModel):
    id: int
    sha: str
    ref: str
    environment: str | None = None
    description: str | None = ""
    creator: dict | None = None
    created_at: datetime
    url: str | None = None


class _Commit(BaseModel):
    sha: str
    html_url: str | None = None
    commit: dict
    files: list[dict] = Field(default_factory=list)


class _Issue(BaseModel):
    number: int
    title: str
    body: str | None = ""
    state: str
    labels: list = Field(default_factory=list)
    created_at: datetime
    html_url: str | None = None
    repository: str | None = None
    user: dict | None = None


def _malformed(what: str, exc: Exception) -> ProviderError:
    return ProviderError(ErrorCode.MALFORMED_RESPONSE, f"GitHub returned malformed {what}: {type(exc).__name__}")


def _issue(raw: dict) -> dict:
    try:
        i = _Issue.model_validate(raw)
    except ValidationError as exc:
        raise _malformed("issue", exc) from exc
    return {
        "number": i.number,
        "title": i.title,
        "body": i.body or "",
        "state": i.state,
        "labels": [lbl["name"] if isinstance(lbl, dict) else str(lbl) for lbl in i.labels],
        "created_at": i.created_at,
        "url": i.html_url,
        "repository": i.repository,
        "author": (i.user or {}).get("login"),
    }


async def list_deployments(args: ListDeploymentsArgs, client) -> dict:
    raw = await client.list_deployments(args.since, args.until)
    if not isinstance(raw, list):
        raise ProviderError(ErrorCode.MALFORMED_RESPONSE, "GitHub deployments payload is not a list")
    items = []
    for entry in raw:
        try:
            d = _Deployment.model_validate(entry)
        except ValidationError as exc:
            raise _malformed("deployment", exc) from exc
        items.append(
            {
                "id": d.id,
                "sha": d.sha,
                "ref": d.ref,
                "environment": d.environment,
                "description": d.description or "",
                "creator": (d.creator or {}).get("login"),
                "created_at": d.created_at,
                "url": d.url,
            }
        )
    return {
        "items": items,
        "data": {"repo": client.repo, "count": len(items)},
        "summary": f"{len(items)} deployment(s)/release(s) in {client.repo}"
        + (f": {', '.join(i['ref'] for i in items[:4])}" if items else ""),
    }


async def list_deployment_changes(args: DeploymentChangesArgs, client) -> dict:
    raw = await client.list_deployment_commits(args.deployment_id)
    if not isinstance(raw, list):
        raise ProviderError(ErrorCode.MALFORMED_RESPONSE, "GitHub commits payload is not a list")
    items = []
    for entry in raw:
        try:
            c = _Commit.model_validate(entry)
        except ValidationError as exc:
            raise _malformed("commit", exc) from exc
        items.append(
            {
                "sha": c.sha,
                "message": (c.commit.get("message") or "").split("\n")[0][:200],
                "author": (c.commit.get("author") or {}).get("name"),
                "date": (c.commit.get("author") or {}).get("date"),
                "files": [f.get("filename") for f in c.files if f.get("filename")][:50],
                "url": c.html_url,
            }
        )
    files = sorted({f for i in items for f in i["files"]})
    return {
        "items": items,
        "data": {"deployment_id": args.deployment_id, "files": files},
        "summary": f"{len(items)} commit(s), {len(files)} file(s) changed",
    }


async def list_issues(args: ListIssuesArgs, client) -> dict:
    raw = await client.list_issues(args.state)
    if not isinstance(raw, list):
        raise ProviderError(ErrorCode.MALFORMED_RESPONSE, "GitHub issues payload is not a list")
    items = [_issue(r) for r in raw]
    return {"items": items, "data": {"repo": client.repo}, "summary": f"{len(items)} issue(s) in {client.repo}"}


async def get_issue(args: IssueNumberArgs, client) -> dict:
    issue = _issue(await client.get_issue(args.number))
    return {"items": [issue], "data": issue, "summary": f"Issue #{issue['number']}: {issue['title']}"}


async def create_issue(args: CreateIssueArgs, client) -> dict:
    issue = _issue(await client.create_issue(args.title, args.body, args.labels))
    return {"items": [issue], "data": issue, "summary": f"Created issue #{issue['number']}"}


async def create_comment(args: CreateCommentArgs, client) -> dict:
    raw = await client.create_comment(args.issue_number, args.body)
    if not isinstance(raw, dict) or "id" not in raw:
        raise ProviderError(ErrorCode.MALFORMED_RESPONSE, "GitHub comment payload missing id")
    data = {"id": raw["id"], "issue_number": args.issue_number, "url": raw.get("html_url")}
    return {"items": [data], "data": data, "summary": f"Commented on issue #{args.issue_number}"}


async def list_comments(args: IssueNumberArgs, client) -> dict:
    raw = await client.list_comments(args.number)
    if not isinstance(raw, list):
        raise ProviderError(ErrorCode.MALFORMED_RESPONSE, "GitHub comments payload is not a list")
    items = [{"id": c.get("id"), "body": c.get("body") or "", "url": c.get("html_url")} for c in raw]
    return {"items": items, "data": {"issue_number": args.number}, "summary": f"{len(items)} comment(s)"}


SPECS = [
    ToolSpec("github.list_deployments", App.GITHUB, "list_deployments",
             "List deployments and releases in a time window.", ToolAccess.READ, RiskLevel.LOW,
             ListDeploymentsArgs, list_deployments),
    ToolSpec("github.list_deployment_changes", App.GITHUB, "list_deployment_commits",
             "List commits and changed files shipped by a deployment.", ToolAccess.READ, RiskLevel.LOW,
             DeploymentChangesArgs, list_deployment_changes),
    ToolSpec("github.list_issues", App.GITHUB, "list_issues",
             "List repository issues (used for duplicate-incident and idempotency checks).",
             ToolAccess.READ, RiskLevel.LOW, ListIssuesArgs, list_issues),
    ToolSpec("github.get_issue", App.GITHUB, "get_issue", "Read a single issue.",
             ToolAccess.READ, RiskLevel.LOW, IssueNumberArgs, get_issue),
    ToolSpec("github.list_comments", App.GITHUB, "list_comments", "List comments on an issue.",
             ToolAccess.READ, RiskLevel.LOW, IssueNumberArgs, list_comments),
    ToolSpec("github.create_issue", App.GITHUB, "create_issue", "Create an incident issue.",
             ToolAccess.WRITE, RiskLevel.MEDIUM, CreateIssueArgs, create_issue,
             verification="reread_issue_and_match_markers"),
    ToolSpec("github.create_comment", App.GITHUB, "create_comment", "Comment on an existing incident issue.",
             ToolAccess.WRITE, RiskLevel.MEDIUM, CreateCommentArgs, create_comment,
             verification="list_comments_and_match_marker"),
]
