from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import App, RiskLevel
from app.errors import ErrorCode, ProviderError
from app.scenarios import parse_dt
from app.tools.base import ToolAccess, ToolSpec


class GetMetadataArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReadRowsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tab: str = Field(min_length=1, max_length=100, pattern=r"^[\w .\-]+$")
    columns: list[str] | None = Field(default=None, max_length=24)
    start: datetime | None = None
    end: datetime | None = None


async def get_metadata(args: GetMetadataArgs, client) -> dict:
    raw = await client.get_metadata()
    sheets = raw.get("sheets") if isinstance(raw, dict) else None
    if not isinstance(sheets, list):
        raise ProviderError(ErrorCode.MALFORMED_RESPONSE, "Sheets metadata missing 'sheets' list")
    tabs = []
    for sheet in sheets:
        props = (sheet or {}).get("properties") or {}
        if "title" not in props:
            raise ProviderError(ErrorCode.MALFORMED_RESPONSE, "Sheet entry without a title")
        grid = props.get("gridProperties") or {}
        tabs.append({"name": props["title"], "row_count": grid.get("rowCount"), "column_count": grid.get("columnCount")})
    title = (raw.get("properties") or {}).get("title", "")
    return {
        "data": {"spreadsheet_id": raw.get("spreadsheetId"), "title": title, "tabs": tabs},
        "summary": f"'{title}' with {len(tabs)} tab(s): {', '.join(t['name'] for t in tabs)}",
    }


def _number(value) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


async def read_rows(args: ReadRowsArgs, client) -> dict:
    raw = await client.get_values(args.tab)
    values = raw.get("values") if isinstance(raw, dict) else None
    if not isinstance(values, list) or not values or not all(isinstance(r, list) for r in values):
        raise ProviderError(ErrorCode.MALFORMED_RESPONSE, f"Sheets returned an unreadable range for '{args.tab}'")
    header = [str(h).strip() for h in values[0]]
    if "timestamp" not in header:
        raise ProviderError(ErrorCode.MALFORMED_RESPONSE, f"Tab '{args.tab}' has no 'timestamp' column")
    requested = args.columns or header
    present = [c for c in requested if c in header]
    missing = [c for c in requested if c not in header]
    ts_index = header.index("timestamp")
    rows, skipped, blanks = [], 0, 0
    for row_number, raw_row in enumerate(values[1:], start=2):
        try:
            ts = parse_dt(raw_row[ts_index])
        except (IndexError, ValueError):
            skipped += 1
            continue
        if (args.start and ts < args.start) or (args.end and ts > args.end):
            continue
        record: dict = {"_row": row_number, "timestamp": ts}
        for column in present:
            if column == "timestamp":
                continue
            idx = header.index(column)
            value = _number(raw_row[idx]) if idx < len(raw_row) else None
            blanks += value is None
            record[column] = value
        rows.append(record)
    warnings = []
    if skipped:
        warnings.append(f"{skipped} row(s) skipped: unparseable timestamp")
    if blanks:
        warnings.append(f"{blanks} blank or non-numeric cell(s)")
    return {
        "items": rows,
        "data": {
            "tab": args.tab,
            "columns_present": present,
            "columns_missing": missing,
            "all_columns": header,
            "row_count": len(rows),
            "first_row": rows[0]["_row"] if rows else None,
            "last_row": rows[-1]["_row"] if rows else None,
        },
        "warnings": warnings,
        "summary": f"{len(rows)} rows from '{args.tab}' ({', '.join(c for c in present if c != 'timestamp')})",
    }


SPECS = [
    ToolSpec(
        name="sheets.get_metadata",
        app=App.SHEETS,
        operation="get_metadata",
        description="Inspect spreadsheet title and tabs.",
        access=ToolAccess.READ,
        risk=RiskLevel.LOW,
        args_model=GetMetadataArgs,
        handler=get_metadata,
    ),
    ToolSpec(
        name="sheets.read_rows",
        app=App.SHEETS,
        operation="get_values",
        description="Read metric rows from a tab, optionally filtered by column and time range.",
        access=ToolAccess.READ,
        risk=RiskLevel.LOW,
        args_model=ReadRowsArgs,
        handler=read_rows,
    ),
]
