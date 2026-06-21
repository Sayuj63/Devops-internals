from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session
from app.exceptions import PlanNotFound
from app.models import Plan
from app.schemas import PlanCreate, PlanOut

router = APIRouter(prefix="/api/v1/plans", tags=["plans"])


@router.get("", response_model=list[PlanOut])
async def list_plans(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> list[PlanOut]:
    rows = (
        await session.execute(select(Plan).order_by(Plan.monthly_inr.asc()))
    ).scalars().all()
    return [PlanOut.model_validate(r) for r in rows]


@router.get("/{plan_id}", response_model=PlanOut)
async def get_plan(
    plan_id: str,
    session: Annotated[AsyncSession, Depends(db_session)],
) -> PlanOut:
    plan = (
        await session.execute(select(Plan).where(Plan.id == plan_id))
    ).scalar_one_or_none()
    if plan is None:
        raise PlanNotFound(f"Plan {plan_id} not found.")
    return PlanOut.model_validate(plan)


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: PlanCreate,
    session: Annotated[AsyncSession, Depends(db_session)],
) -> PlanOut:
    plan = Plan(**body.model_dump())
    session.add(plan)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise PlanNotFound(f"Plan name '{body.name}' already exists.") from exc
    await session.refresh(plan)
    return PlanOut.model_validate(plan)
