from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import MsisdnPoolExhausted
from app.metrics import msisdn_pool_remaining
from app.models import MsisdnPoolEntry


class MsisdnPool:
    # Locking strategy:
    # On Postgres we rely on `SELECT ... FOR UPDATE SKIP LOCKED` so concurrent
    # activations never hand out the same MSISDN even under heavy parallelism;
    # rows already locked by another transaction are skipped, and an UPDATE
    # claims the row by setting is_used=true atomically. On SQLite (tests) the
    # statement degrades into a plain SELECT inside the surrounding transaction
    # because sqlite serialises writes anyway, so correctness is preserved.

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def allocate(self, iccid: str) -> str:
        dialect = self._session.bind.dialect.name if self._session.bind else "sqlite"

        stmt = select(MsisdnPoolEntry).where(MsisdnPoolEntry.is_used.is_(False)).limit(1)
        if dialect == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)

        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise MsisdnPoolExhausted("No MSISDNs left in the pool.")

        row.is_used = True
        row.assigned_iccid = iccid
        row.assigned_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self.refresh_gauge()
        return row.msisdn

    async def release(self, msisdn: str) -> None:
        await self._session.execute(
            update(MsisdnPoolEntry)
            .where(MsisdnPoolEntry.msisdn == msisdn)
            .values(is_used=False, assigned_iccid=None, assigned_at=None)
        )
        await self.refresh_gauge()

    async def remaining(self) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(MsisdnPoolEntry)
            .where(MsisdnPoolEntry.is_used.is_(False))
        )
        return int(result.scalar_one())

    async def refresh_gauge(self) -> None:
        msisdn_pool_remaining.set(await self.remaining())
