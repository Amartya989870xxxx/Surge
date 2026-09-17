from __future__ import annotations

from app.tools import github, sheets, slack
from app.tools.base import ToolSpec


class ToolRegistry:
    """Explicit allowlist of operations. The agent cannot call anything not registered here."""

    def __init__(self, specs: list[ToolSpec]):
        self._specs = {spec.name: spec for spec in specs}

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def list(self) -> list[ToolSpec]:
        return list(self._specs.values())

    def describe(self) -> list[dict]:
        return [spec.describe() for spec in self._specs.values()]


def build_registry() -> ToolRegistry:
    return ToolRegistry([*sheets.SPECS, *github.SPECS, *slack.SPECS])
