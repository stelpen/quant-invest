"""Scheduled background jobs for data updates and signal generation.

Uses APScheduler's BackgroundScheduler (non-blocking) to run:
    - Daily data update after market close (16:00 CST).
    - Signal generation + notification (16:30 CST).
    - An optional first-run data sync on startup.

All times use the Asia/Shanghai timezone.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

_TZ = "Asia/Shanghai"


class Scheduler:
    """Wrap APScheduler with quant-specific jobs.

    Args:
        update_fn: Callable that refreshes market data (no args).
        signal_fn: Callable that generates + dispatches signals (no args).
    """

    def __init__(
        self,
        update_fn: Optional[Callable[[], Any]] = None,
        signal_fn: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._scheduler = BackgroundScheduler(timezone=_TZ)
        self._update_fn = update_fn
        self._signal_fn = signal_fn
        self._started = False

    def start(self, run_initial_sync: bool = False) -> None:
        """Register jobs and start the scheduler.

        Args:
            run_initial_sync: If True, run the data update once immediately
                on startup (useful for first run).
        """
        if self._started:
            logger.warning("Scheduler already started.")
            return

        if self._update_fn is not None:
            self._scheduler.add_job(
                self._safe(self._update_fn, "data-update"),
                trigger=CronTrigger(hour=16, minute=0, timezone=_TZ),
                id="daily_data_update",
                replace_existing=True,
            )
            logger.info("Registered job: daily data update @ 16:00 CST")

        if self._signal_fn is not None:
            self._scheduler.add_job(
                self._safe(self._signal_fn, "signal-generation"),
                trigger=CronTrigger(hour=16, minute=30, timezone=_TZ),
                id="daily_signal_generation",
                replace_existing=True,
            )
            logger.info("Registered job: signal generation @ 16:30 CST")

        self._scheduler.start()
        self._started = True
        logger.info("Scheduler started.")

        if run_initial_sync and self._update_fn is not None:
            logger.info("Running initial data sync on startup...")
            self._safe(self._update_fn, "initial-sync")()

    def stop(self) -> None:
        """Shut down the scheduler."""
        if self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False
            logger.info("Scheduler stopped.")

    def add_job(self, func: Callable, trigger: Any, job_id: str, **kwargs: Any) -> None:
        """Register an arbitrary job.

        Args:
            func: Callable to execute.
            trigger: An APScheduler trigger instance.
            job_id: Unique job identifier.
            **kwargs: Extra keyword args passed to ``add_job``.
        """
        self._scheduler.add_job(
            self._safe(func, job_id),
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs,
        )
        logger.info(f"Registered job: {job_id}")

    def get_jobs(self) -> list[dict[str, Any]]:
        """Return metadata for all scheduled jobs."""
        return [
            {
                "id": job.id,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in self._scheduler.get_jobs()
        ]

    @staticmethod
    def _safe(func: Callable, name: str) -> Callable[[], None]:
        """Wrap a job callable so exceptions are logged, not swallowed."""

        def _runner() -> None:
            logger.info(f"Job '{name}' started.")
            try:
                func()
                logger.info(f"Job '{name}' completed.")
            except Exception as exc:  # noqa: BLE001 - jobs must not crash scheduler
                logger.error(f"Job '{name}' failed: {exc}")

        return _runner
