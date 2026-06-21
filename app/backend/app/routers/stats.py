from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session
from app.models import AuditEvent, MsisdnPoolEntry, Plan, SIM, SimStatus
from app.schemas import ActivationBucket, StatsOut, StatusCount, TopPlan

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
async def stats(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> StatsOut:
    total = int(
        (await session.execute(select(func.count()).select_from(SIM))).scalar_one()
    )

    status_rows = (
        await session.execute(
            select(SIM.status, func.count()).group_by(SIM.status)
        )
    ).all()
    counts = [StatusCount(status=s, count=int(c)) for s, c in status_rows]
    by_status: dict[str, int] = {st.value: 0 for st in SimStatus}
    for s, c in status_rows:
        by_status[s.value if hasattr(s, "value") else str(s)] = int(c)

    now = datetime.now(timezone.utc)
    bucket_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=23)

    buckets: list[ActivationBucket] = []
    for h in range(24):
        b_from = bucket_start + timedelta(hours=h)
        b_to = b_from + timedelta(hours=1)
        activated = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.to_status == SimStatus.ACTIVE)
                    .where(AuditEvent.created_at >= b_from)
                    .where(AuditEvent.created_at < b_to)
                )
            ).scalar_one()
        )
        suspended = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.to_status == SimStatus.SUSPENDED)
                    .where(AuditEvent.created_at >= b_from)
                    .where(AuditEvent.created_at < b_to)
                )
            ).scalar_one()
        )
        buckets.append(ActivationBucket(ts=b_from, activated=activated, suspended=suspended))

    activations_24h_total = sum(b.activated for b in buckets)

    latency_expr = func.avg(
        func.extract("epoch", SIM.activated_at) - func.extract("epoch", SIM.allocated_at)
    )
    dialect = session.bind.dialect.name if session.bind else "sqlite"
    if dialect == "sqlite":
        latency_expr = func.avg(
            (func.julianday(SIM.activated_at) - func.julianday(SIM.allocated_at))
            * 86400.0
        )

    mean_latency_raw = (
        await session.execute(
            select(latency_expr)
            .where(SIM.activated_at.is_not(None))
            .where(SIM.allocated_at.is_not(None))
        )
    ).scalar_one()
    mean_latency_s = float(mean_latency_raw) if mean_latency_raw is not None else None
    mean_latency_ms = round(mean_latency_s * 1000.0, 1) if mean_latency_s is not None else None

    pool_remaining = int(
        (
            await session.execute(
                select(func.count())
                .select_from(MsisdnPoolEntry)
                .where(MsisdnPoolEntry.is_used.is_(False))
            )
        ).scalar_one()
    )

    top_rows = (
        await session.execute(
            select(Plan.id, Plan.name, func.count(SIM.iccid).label("active"))
            .join(SIM, SIM.plan_id == Plan.id)
            .where(SIM.status == SimStatus.ACTIVE)
            .group_by(Plan.id, Plan.name)
            .order_by(desc("active"))
            .limit(5)
        )
    ).all()
    top_plans = [
        TopPlan(plan_id=pid, plan_name=name, active_sims=int(active))
        for pid, name, active in top_rows
    ]

    return StatsOut(
        total=total,
        total_sims=total,
        by_status=by_status,
        counts_by_status=counts,
        activations_last_24h=buckets,
        activations_last_24h_total=activations_24h_total,
        mean_activation_latency_ms=mean_latency_ms,
        mean_activation_latency_seconds=mean_latency_s,
        msisdn_pool_remaining=pool_remaining,
        top_plans=top_plans,
    )
