from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, sim_service_dep
from app.exceptions import InvalidIccid, SimNotFound
from app.models import SIM, SimStatus
from app.schemas import (
    AllocateRequest,
    BulkProvisionRequest,
    BulkProvisionResult,
    Page,
    SimOut,
    TransitionRequest,
    validate_iccid,
)
from app.services.sim_service import SimService

router = APIRouter(prefix="/api/v1/sims", tags=["sims"])


def _iccid_path(iccid: str) -> str:
    try:
        return validate_iccid(iccid)
    except ValueError as exc:
        raise InvalidIccid(str(exc)) from exc


@router.get("", response_model=Page[SimOut])
async def list_sims(
    session: Annotated[AsyncSession, Depends(db_session)],
    status_filter: SimStatus | None = Query(default=None, alias="status"),
    plan_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Page[SimOut]:
    stmt = select(SIM)
    count_stmt = select(func.count()).select_from(SIM)

    if status_filter is not None:
        stmt = stmt.where(SIM.status == status_filter)
        count_stmt = count_stmt.where(SIM.status == status_filter)
    if plan_id is not None:
        stmt = stmt.where(SIM.plan_id == plan_id)
        count_stmt = count_stmt.where(SIM.plan_id == plan_id)

    stmt = stmt.order_by(SIM.last_transition_at.desc()).limit(limit).offset(offset)
    rows = (await session.execute(stmt)).scalars().all()
    total = int((await session.execute(count_stmt)).scalar_one())
    return Page[SimOut](
        items=[SimOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{iccid}", response_model=SimOut)
async def get_sim(
    iccid: str,
    session: Annotated[AsyncSession, Depends(db_session)],
) -> SimOut:
    iccid = _iccid_path(iccid)
    sim = (
        await session.execute(select(SIM).where(SIM.iccid == iccid))
    ).scalar_one_or_none()
    if sim is None:
        raise SimNotFound(f"SIM with ICCID {iccid} not found.")
    return SimOut.model_validate(sim)


async def _commit_and_return(session: AsyncSession, sim) -> SimOut:
    await session.commit()
    await session.refresh(sim)
    return SimOut.model_validate(sim)


@router.post("/{iccid}/allocate", response_model=SimOut)
async def allocate(
    iccid: str,
    body: AllocateRequest,
    service: Annotated[SimService, Depends(sim_service_dep)],
    session: Annotated[AsyncSession, Depends(db_session)],
) -> SimOut:
    iccid = _iccid_path(iccid)
    sim = await service.allocate(iccid, body.plan_id, body.actor, body.reason)
    return await _commit_and_return(session, sim)


@router.post("/{iccid}/activate", response_model=SimOut)
async def activate(
    iccid: str,
    body: TransitionRequest,
    service: Annotated[SimService, Depends(sim_service_dep)],
    session: Annotated[AsyncSession, Depends(db_session)],
) -> SimOut:
    iccid = _iccid_path(iccid)
    sim = await service.activate(iccid, body.actor, body.reason)
    return await _commit_and_return(session, sim)


@router.post("/{iccid}/suspend", response_model=SimOut)
async def suspend(
    iccid: str,
    body: TransitionRequest,
    service: Annotated[SimService, Depends(sim_service_dep)],
    session: Annotated[AsyncSession, Depends(db_session)],
) -> SimOut:
    iccid = _iccid_path(iccid)
    sim = await service.suspend(iccid, body.actor, body.reason)
    return await _commit_and_return(session, sim)


@router.post("/{iccid}/resume", response_model=SimOut)
async def resume(
    iccid: str,
    body: TransitionRequest,
    service: Annotated[SimService, Depends(sim_service_dep)],
    session: Annotated[AsyncSession, Depends(db_session)],
) -> SimOut:
    iccid = _iccid_path(iccid)
    sim = await service.resume(iccid, body.actor, body.reason)
    return await _commit_and_return(session, sim)


@router.post("/{iccid}/port_out", response_model=SimOut)
async def port_out(
    iccid: str,
    body: TransitionRequest,
    service: Annotated[SimService, Depends(sim_service_dep)],
    session: Annotated[AsyncSession, Depends(db_session)],
) -> SimOut:
    iccid = _iccid_path(iccid)
    sim = await service.port_out(iccid, body.actor, body.reason)
    return await _commit_and_return(session, sim)


@router.post("/{iccid}/recycle", response_model=SimOut)
async def recycle(
    iccid: str,
    body: TransitionRequest,
    service: Annotated[SimService, Depends(sim_service_dep)],
    session: Annotated[AsyncSession, Depends(db_session)],
) -> SimOut:
    iccid = _iccid_path(iccid)
    sim = await service.recycle(iccid, body.actor, body.reason)
    return await _commit_and_return(session, sim)


@router.post(
    "/bulk_provision",
    response_model=BulkProvisionResult,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_provision(
    body: BulkProvisionRequest,
    session: Annotated[AsyncSession, Depends(db_session)],
) -> BulkProvisionResult:
    inserted = 0
    skipped = 0
    failed: list[dict[str, str]] = []

    existing_iccids = set(
        (
            await session.execute(
                select(SIM.iccid).where(SIM.iccid.in_([i.iccid for i in body.items]))
            )
        )
        .scalars()
        .all()
    )

    for item in body.items:
        if item.iccid in existing_iccids:
            skipped += 1
            continue
        sim = SIM(
            iccid=item.iccid,
            imsi=item.imsi,
            plan_id=item.plan_id,
            status=SimStatus.PENDING,
        )
        session.add(sim)
        try:
            await session.flush()
            inserted += 1
        except IntegrityError as exc:
            await session.rollback()
            failed.append({"iccid": item.iccid, "error": str(exc.orig)[:200]})

    await session.commit()
    return BulkProvisionResult(inserted=inserted, skipped=skipped, failed=failed)
