from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.services.hlr_adapter import HlrClient, get_hlr_client
from app.services.msisdn_pool import MsisdnPool
from app.services.sim_service import SimService


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for s in get_session():
        yield s


def hlr_dep() -> HlrClient:
    return get_hlr_client()


async def msisdn_pool_dep(
    session: AsyncSession = Depends(db_session),
) -> MsisdnPool:
    return MsisdnPool(session)


async def sim_service_dep(
    request: Request,
    session: AsyncSession = Depends(db_session),
    hlr: HlrClient = Depends(hlr_dep),
    pool: MsisdnPool = Depends(msisdn_pool_dep),
) -> SimService:
    rid = getattr(request.state, "request_id", None)
    return SimService(session=session, hlr=hlr, msisdn_pool=pool, request_id=rid)
