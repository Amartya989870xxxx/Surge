"""Independent post-action verification: re-read provider state and compare with what we intended."""

from dataclasses import dataclass, field

from app.actions.proposals import REPORT_HEADER
from app.enums import VerificationStatus
from app.errors import ErrorCode
from app.tools.base import ToolContext
from app.tools.runner import ToolRunner


@dataclass
class VerificationResult:
    status: VerificationStatus
    method: str
    checks: list[dict] = field(default_factory=list)
    expected: dict = field(default_factory=dict)
    observed: dict = field(default_factory=dict)
    error_code: str | None = None

    @property
    def confidence(self) -> float:
        if self.status == VerificationStatus.VERIFIED:
            return 1.0
        if not self.checks:
            return 0.0
        return round(sum(c["passed"] for c in self.checks) / len(self.checks), 2)


async def verify_issue(runner: ToolRunner, ctx: ToolContext, *, number: int, repo: str, title: str, markers: list[str]) -> VerificationResult:
    expected = {"repository": repo, "number": number, "title": title, "markers": markers, "state": "open"}
    res = await runner.call(ctx, "github.get_issue", {"number": number}, purpose=f"Re-read issue #{number} to verify it")
    if not res.success:
        status = VerificationStatus.FAILED if res.error.code == ErrorCode.NOT_FOUND else VerificationStatus.UNKNOWN
        return VerificationResult(status, "reread_issue_and_match_markers", expected=expected, error_code=res.error.code)
    issue = res.data
    body = issue.get("body") or ""
    checks = [
        {"check": "issue exists", "passed": True},
        {"check": "repository matches", "passed": issue.get("repository") in (None, repo) and bool(repo)},
        {"check": "title matches", "passed": issue.get("title") == title},
        {"check": "report section present", "passed": REPORT_HEADER in body},
        *[{"check": f"marker {m} present", "passed": m in body} for m in markers],
        {"check": "issue is open", "passed": issue.get("state") == "open"},
    ]
    observed = {
        "repository": issue.get("repository"),
        "number": issue.get("number"),
        "title": issue.get("title"),
        "state": issue.get("state"),
        "url": issue.get("url"),
        "body_length": len(body),
    }
    status = VerificationStatus.VERIFIED if all(c["passed"] for c in checks) else VerificationStatus.FAILED
    return VerificationResult(status, "reread_issue_and_match_markers", checks, expected, observed)


async def verify_comment(runner: ToolRunner, ctx: ToolContext, *, issue_number: int, marker: str) -> VerificationResult:
    expected = {"issue_number": issue_number, "marker": marker}
    comment, ok = await find_comment_by_marker(runner, ctx, issue_number, marker)
    if not ok:
        return VerificationResult(VerificationStatus.UNKNOWN, "list_comments_and_match_marker", expected=expected, error_code="LOOKUP_FAILED")
    checks = [
        {"check": "comment with action marker exists", "passed": comment is not None},
        {"check": "report section present", "passed": bool(comment) and REPORT_HEADER in comment.get("body", "")},
    ]
    observed = {"comment_id": comment.get("id"), "url": comment.get("url")} if comment else {}
    status = VerificationStatus.VERIFIED if all(c["passed"] for c in checks) else VerificationStatus.FAILED
    return VerificationResult(status, "list_comments_and_match_marker", checks, expected, observed)


async def find_issue_by_marker(runner: ToolRunner, ctx: ToolContext, marker: str) -> tuple[dict | None, bool]:
    res = await runner.call(ctx, "github.list_issues", {"state": "all"}, purpose=f"Look for an issue carrying {marker}")
    if not res.success:
        return None, False
    return next((i for i in res.items if marker in (i.get("body") or "")), None), True


async def find_comment_by_marker(runner: ToolRunner, ctx: ToolContext, issue_number: int, marker: str) -> tuple[dict | None, bool]:
    res = await runner.call(ctx, "github.list_comments", {"number": issue_number}, purpose=f"Look for a comment carrying {marker}")
    if not res.success:
        return None, False
    return next((c for c in res.items if marker in (c.get("body") or "")), None), True
