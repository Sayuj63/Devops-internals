from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session
from app.models import AuditEvent, SimStatus
from app.schemas import AuditEventOut, Page

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=Page[AuditEventOut])
async def list_audit(
    session: Annotated[AsyncSession, Depends(db_session)],
    iccid: str | None = Query(default=None),
    to_status: SimStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Page[AuditEventOut]:
    stmt = select(AuditEvent)
    count_stmt = select(func.count()).select_from(AuditEvent)
    if iccid is not None:
        stmt = stmt.where(AuditEvent.sim_iccid == iccid)
        count_stmt = count_stmt.where(AuditEvent.sim_iccid == iccid)
    if to_status is not None:
        stmt = stmt.where(AuditEvent.to_status == to_status)
        count_stmt = count_stmt.where(AuditEvent.to_status == to_status)

    stmt = stmt.order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)
    rows = (await session.execute(stmt)).scalars().all()
    total = int((await session.execute(count_stmt)).scalar_one())
    return Page[AuditEventOut](
        items=[AuditEventOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
