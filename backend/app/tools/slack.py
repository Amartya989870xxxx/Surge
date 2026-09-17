from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.enums import App, RiskLevel
from app.errors import ErrorCode, ProviderError
from app.observability.logging import redact
from app.tools.base import ToolAccess, ToolSpec

MAX_TEXT = 500


class SearchMessagesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    terms: list[str] = Field(min_length=1, max_length=12)
    since: datetime
    until: datetime
    limit: int = Field(default=50, ge=1, le=100)

    @field_validator("terms")
    @classmethod
    def _terms(cls, terms: list[str]) -> list[str]:
        for term in terms:
            if not (1 <= len(term) <= 40) or any(ch in term for ch in '<>"`'):
                raise ValueError(f"invalid search term: {term!r}")
        return terms


class _Channel(BaseModel):
    id: str
    name: str | None = None


class _Match(BaseModel):
    channel: _Channel
    text: str
    ts: str
    user: str | None = None
    username: str | None = None
    permalink: str | None = None


async def search_messages(args: SearchMessagesArgs, client) -> dict:
    raw = await client.search_messages(args.terms, args.since, args.until, args.limit)
    matches = ((raw or {}).get("messages") or {}).get("matches") if isinstance(raw, dict) else None
    if not isinstance(matches, list):
        raise ProviderError(ErrorCode.MALFORMED_RESPONSE, "Slack search payload has no matches list")
    items = []
    for entry in matches:
        try:
            m = _Match.model_validate(entry)
            observed = datetime.fromtimestamp(float(m.ts), tz=UTC)
        except (ValidationError, ValueError, TypeError) as exc:
            raise ProviderError(
                ErrorCode.MALFORMED_RESPONSE, f"Slack returned a malformed message ({type(exc).__name__})"
            ) from exc
        text = redact(m.text, emails=True) or ""
        items.append(
            {
                "id": f"{m.channel.id}:{m.ts}",
                "channel_id": m.channel.id,
                "channel_name": m.channel.name or m.channel.id,
                "user": m.username or m.user or "unknown",
                "text": text[:MAX_TEXT] + ("…" if len(text) > MAX_TEXT else ""),
                "observed_at": observed,
                "url": m.permalink,
            }
        )
    return {
        "items": items,
        "data": {"total": (raw.get("messages") or {}).get("total", len(items)), "terms": args.terms},
        "summary": f"{len(items)} matching message(s)",
    }


SPECS = [
    ToolSpec(
        name="slack.search_messages",
        app=App.SLACK,
        operation="search_messages",
        description="Search Slack messages by keyword within a time window.",
        access=ToolAccess.READ,
        risk=RiskLevel.LOW,
        args_model=SearchMessagesArgs,
        handler=search_messages,
    )
]
