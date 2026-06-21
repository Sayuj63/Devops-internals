from __future__ import annotations

import asyncio
import os
import signal
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.metrics import (
    msisdn_pool_remaining,
    sim_state_transitions_total,
)
from app.models import MsisdnPoolEntry, SIM, SimStatus


LIVENESS_FILE = Path(os.environ.get("WORKER_LIVENESS_FILE", "/tmp/worker.alive"))
TICK_SECONDS = float(os.environ.get("WORKER_TICK_SECONDS", "5"))
STUCK_ALLOCATED_AFTER_MIN = int(os.environ.get("WORKER_STUCK_AFTER_MIN", "30"))

log = structlog.get_logger("worker")
_shutdown = asyncio.Event()


def _touch_liveness() -> None:
    try:
        LIVENESS_FILE.touch(exist_ok=True)
    except OSError as exc:
        log.warning("liveness_touch_failed", error=str(exc))


async def _refresh_pool_gauge() -> None:
    async with SessionLocal() as session:
        remaining = (
            await session.execute(
                select(MsisdnPoolEntry).where(MsisdnPoolEntry.is_used.is_(False))
            )
        ).scalars().all()
        msisdn_pool_remaining.set(len(remaining))


async def _reap_stuck_allocations() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STUCK_ALLOCATED_AFTER_MIN)
    async with SessionLocal() as session:
        stuck = (
            await session.execute(
                select(SIM)
                .where(SIM.status == SimStatus.ALLOCATED)
                .where(SIM.allocated_at.is_not(None))
                .where(SIM.allocated_at < cutoff)
                .limit(50)
            )
        ).scalars().all()
        if not stuck:
            return 0
        for sim in stuck:
            log.warning(
                "reaping_stuck_allocation",
                iccid=sim.iccid,
                allocated_at=sim.allocated_at.isoformat() if sim.allocated_at else None,
            )
            sim_state_transitions_total.labels(
                **{"from": SimStatus.ALLOCATED.value, "to": SimStatus.PENDING.value}
            ).inc()
        await session.commit()
        return len(stuck)


async def _tick() -> None:
    _touch_liveness()
    await _refresh_pool_gauge()
    reaped = await _reap_stuck_allocations()
    if reaped:
        log.info("worker_tick", reaped=reaped)


def _install_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    def _handler(sig: int) -> None:
        log.info("worker_signal_received", signal=signal.Signals(sig).name)
        _shutdown.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handler, sig)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: _shutdown.set())


async def main() -> int:
    settings = get_settings()
    log.info(
        "worker_starting",
        tick_seconds=TICK_SECONDS,
        stuck_after_min=STUCK_ALLOCATED_AFTER_MIN,
        liveness_file=str(LIVENESS_FILE),
        db_url=settings.database_url.split("@")[-1],
    )
    _install_signal_handlers(asyncio.get_running_loop())
    _touch_liveness()
    while not _shutdown.is_set():
        try:
            await _tick()
        except Exception as exc:
            log.error("worker_tick_failed", error=str(exc), exc_info=True)
        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=TICK_SECONDS)
        except asyncio.TimeoutError:
            pass
    log.info("worker_stopped")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
