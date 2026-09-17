import logging
import re

_SECRET_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[abeprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"ya29\.[A-Za-z0-9._-]{20,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    re.compile(r"org_[A-Za-z0-9]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    re.compile(r"AQ\.[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)((?:api[_-]?key|x-goog-api-key)[\"']?\s*[:=]\s*[\"']?)[A-Za-z0-9._\-]{16,}"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)((?:access|refresh)_token[\"']?\s*[:=]\s*[\"']?)[A-Za-z0-9._~+/=-]{8,}"),
]
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact(text: str | None, *, emails: bool = False) -> str | None:
    if text is None:
        return None
    out = text
    for pattern in _SECRET_PATTERNS:
        if pattern.groups:
            out = pattern.sub(lambda m: f"{m.group(1)}[REDACTED]", out)
        else:
            out = pattern.sub("[REDACTED]", out)
    if emails:
        out = _EMAIL.sub("[email]", out)
    return out


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if record.args:
            record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s | %(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger("surge")
    root.handlers = [handler]
    root.setLevel(level)
    root.propagate = False
