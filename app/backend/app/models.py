from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class SimStatus(str, enum.Enum):
    PENDING = "PENDING"
    ALLOCATED = "ALLOCATED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    PORTED = "PORTED"
    RECYCLED = "RECYCLED"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    data_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    voice_min: Mapped[int] = mapped_column(Integer, nullable=False)
    sms_count: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    sims: Mapped[list["SIM"]] = relationship(back_populates="plan")


class SIM(Base):
    __tablename__ = "sims"

    iccid: Mapped[str] = mapped_column(String(20), primary_key=True)
    imsi: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    msisdn: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True)
    status: Mapped[SimStatus] = mapped_column(
        SAEnum(SimStatus, name="sim_status"),
        default=SimStatus.PENDING,
        nullable=False,
        index=True,
    )
    plan_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provisioning_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    allocated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_transition_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    plan: Mapped[Plan | None] = relationship(back_populates="sims", lazy="joined")
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="sim", cascade="all, delete-orphan"
    )


class MsisdnPoolEntry(Base):
    __tablename__ = "msisdn_pool"

    msisdn: Mapped[str] = mapped_column(String(16), primary_key=True)
    is_used: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    assigned_iccid: Mapped[str | None] = mapped_column(String(20), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    sim_iccid: Mapped[str] = mapped_column(
        String(20), ForeignKey("sims.iccid", ondelete="CASCADE"), nullable=False
    )
    actor: Mapped[str] = mapped_column(String(80), default="system", nullable=False)
    from_status: Mapped[SimStatus | None] = mapped_column(
        SAEnum(SimStatus, name="sim_status"), nullable=True
    )
    to_status: Mapped[SimStatus] = mapped_column(
        SAEnum(SimStatus, name="sim_status"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )

    sim: Mapped[SIM] = relationship(back_populates="audit_events")


Index("ix_sims_status_plan", SIM.status, SIM.plan_id)
Index("ix_audit_created_sim", AuditEvent.created_at.desc(), AuditEvent.sim_iccid)
