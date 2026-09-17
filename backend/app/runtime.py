import asyncio
import logging
from collections.abc import Coroutine

from app.connectors.manager import ConnectorManager, ConnectorSet
from app.db.models import Investigation
from app.scenarios import WorldRegistry

logger = logging.getLogger("surge.runtime")


class Runtime:
    """In-process task, cancellation and connector bookkeeping for active runs."""

    def __init__(self, connectors: ConnectorManager, worlds: WorldRegistry):
        self.connectors = connectors
        self.worlds = worlds
        self._tasks: dict[str, asyncio.Task] = {}
        self._cancelled: set[str] = set()
        self._connector_sets: dict[str, ConnectorSet] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def spawn(self, key: str, coro: Coroutine) -> asyncio.Task:
        task = asyncio.create_task(coro, name=f"surge:{key}")
        self._tasks[key] = task

        def _done(t: asyncio.Task, k: str = key) -> None:
            if self._tasks.get(k) is t:
                self._tasks.pop(k, None)
            if not t.cancelled() and t.exception() is not None:
                logger.error("Background task %s failed: %r", k, t.exception())

        task.add_done_callback(_done)
        return task

    def is_running(self, key: str) -> bool:
        task = self._tasks.get(key)
        return task is not None and not task.done()

    def running_keys(self, prefix: str = "") -> list[str]:
        return [k for k, t in self._tasks.items() if k.startswith(prefix) and not t.done()]

    async def cancel(self, key: str) -> bool:
        self._cancelled.add(key)
        task = self._tasks.get(key)
        if task is None or task.done():
            return False
        task.cancel()
        await asyncio.wait({task}, timeout=5)
        return True

    def is_cancelled(self, key: str) -> bool:
        return key in self._cancelled

    def lock(self, key: str) -> asyncio.Lock:
        return self._locks.setdefault(key, asyncio.Lock())

    def connectors_for(self, inv: Investigation) -> ConnectorSet:
        cached = self._connector_sets.get(inv.id)
        if cached is not None:
            return cached
        profile = (inv.connector_profile or {}).get("apps", {})
        world = self.worlds.get(inv.world_key, inv.scenario_id) if inv.world_key and inv.scenario_id else None
        built = self.connectors.build(
            profile,
            world=world,
            faults=inv.fault_injection,
            latency_ms=(inv.connector_profile or {}).get("latency_ms", 0),
            user_id=inv.session_id,
        )
        self._connector_sets[inv.id] = built
        return built

    def forget(self, investigation_id: str) -> None:
        self._connector_sets.pop(investigation_id, None)
        self._cancelled.discard(investigation_id)

    async def shutdown(self) -> None:
        tasks = [t for t in self._tasks.values() if not t.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.wait(tasks, timeout=5)
