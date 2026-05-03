"""Background scheduler scaffolding.

Two integration paths are provided. Pick the one that matches your
deployment topology:

1) Inline (default, this file)
   Zero extra dependencies. Good for development and a single-worker
   deployment. Spawns asyncio.Tasks inside the FastAPI process and shuts
   them down with the lifespan.

2) APScheduler  (in-process cron-style scheduling)
   pip install apscheduler
   ```python
   from apscheduler.schedulers.asyncio import AsyncIOScheduler
   aps = AsyncIOScheduler()
   aps.add_job(sweep_recent_alerts, "interval", seconds=60)
   aps.start()
   ```

3) Celery  (distributed, retries, dead-letter, etc.)
   Recommended once you scale beyond one worker. Move `evaluate_signal`
   into a Celery task and replace the inline `asyncio.create_task` call
   inside `signal_service.create_signal` with `evaluate_signal.delay(...)`.

Until you swap one in, the FastAPI app still evaluates alerts inline on
every signal creation (see signal_service.create_signal). The placeholder
job below shows how a periodic re-evaluation would look.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# A no-deps periodic task primitive
# ---------------------------------------------------------------------------

class PeriodicTask:
    """Run an async callable every `interval_seconds` until stopped.

    Failures inside the job are logged but do not break the loop. The
    next iteration is gated by the same `_stopping` event so a graceful
    shutdown completes within ~one tick of `stop()`.
    """

    def __init__(
        self,
        job: Callable[[], Awaitable[None]],
        interval_seconds: float,
        name: str,
    ) -> None:
        self.job = job
        self.interval = max(0.5, float(interval_seconds))
        self.name = name
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    def start(self) -> None:
        if self._task is not None:
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._loop(), name=f"periodic:{self.name}")
        logger.info("Started periodic task '%s' every %.1fs", self.name, self.interval)

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        self._task = None
        logger.info("Stopped periodic task '%s'", self.name)

    async def _loop(self) -> None:
        while not self._stopping.is_set():
            try:
                await self.job()
            except Exception:  # noqa: BLE001
                logger.exception("Periodic task '%s' raised", self.name)

            try:
                # Wait either for the interval to elapse or for stop() to fire.
                await asyncio.wait_for(self._stopping.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                continue
            else:
                break  # stop() was called


# ---------------------------------------------------------------------------
# Tiny scheduler registry — the FastAPI lifespan starts/stops these.
# ---------------------------------------------------------------------------

class _SchedulerRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, PeriodicTask] = {}

    def register(self, task: PeriodicTask) -> None:
        if task.name in self._tasks:
            raise ValueError(f"Periodic task '{task.name}' already registered")
        self._tasks[task.name] = task

    def start_all(self) -> None:
        for t in self._tasks.values():
            t.start()

    async def stop_all(self) -> None:
        for t in list(self._tasks.values()):
            await t.stop()


scheduler = _SchedulerRegistry()


# ---------------------------------------------------------------------------
# Sample job — wire this in once you want periodic sweeps.
# ---------------------------------------------------------------------------

async def sweep_recent_alerts(window_seconds: int = 300) -> None:
    """Re-evaluate every signal from the last `window_seconds` against all
    active rules. Useful when a new rule should retroactively notify the
    user about a signal that happened just before the rule was created.

    Wire it up in main.py's lifespan:

        from app.tasks import PeriodicTask, scheduler
        scheduler.register(PeriodicTask(sweep_recent_alerts, 60, "alert-sweep"))

        @asynccontextmanager
        async def lifespan(app):
            scheduler.start_all()
            yield
            await scheduler.stop_all()
    """
    # Imported lazily so the module can be imported without a DB connection.
    from app.core.database import AsyncSessionLocal
    from app.services import alert_service

    since = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    async with AsyncSessionLocal() as db:
        fired = await alert_service.evaluate_recent_signals(db, since=since)
    if fired:
        logger.info("Periodic sweep fired %d alerts in the last %ds", fired, window_seconds)
