from __future__ import annotations

import re
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import SimStatus


ICCID_RE = re.compile(r"^\d{19,20}$")
IMSI_RE = re.compile(r"^\d{15}$")
MSISDN_RE = re.compile(r"^\+\d{8,15}$")


def luhn_check(number: str) -> bool:
    # Iterate right-to-left, doubling every second digit and summing modulo 10.
    total = 0
    for i, ch in enumerate(reversed(number)):
        if not ch.isdigit():
            return False
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def validate_iccid(value: str) -> str:
    if not ICCID_RE.match(value):
        raise ValueError("ICCID must be 19 or 20 digits")
    if not luhn_check(value):
        raise ValueError("ICCID failed Luhn check")
    return value


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class PlanBase(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    data_gb: int = Field(ge=0, le=10_000)
    voice_min: int = Field(ge=0, le=1_000_000)
    sms_count: int = Field(ge=0, le=1_000_000)
    monthly_inr: int = Field(ge=0, le=1_000_000)


class PlanCreate(PlanBase):
    pass


class PlanOut(PlanBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    is_active: bool
    created_at: datetime


class SimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    iccid: str
    imsi: str
    msisdn: str | None
    status: SimStatus
    plan_id: str | None
    provisioning_ref: str | None
    allocated_at: datetime | None
    activated_at: datetime | None
    last_transition_at: datetime
    created_at: datetime


class TransitionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
    actor: str = Field(default="operator", max_length=80)


class AllocateRequest(TransitionRequest):
    plan_id: str | None = None


class BulkProvisionItem(BaseModel):
    iccid: str
    imsi: str
    plan_id: str | None = None

    @field_validator("iccid")
    @classmethod
    def _v_iccid(cls, v: str) -> str:
        return validate_iccid(v)

    @field_validator("imsi")
    @classmethod
    def _v_imsi(cls, v: str) -> str:
        if not IMSI_RE.match(v):
            raise ValueError("IMSI must be exactly 15 digits")
        return v


class BulkProvisionRequest(BaseModel):
    items: list[BulkProvisionItem] = Field(min_length=1, max_length=5000)
    actor: str = Field(default="bulk-loader", max_length=80)


class BulkProvisionResult(BaseModel):
    inserted: int
    skipped: int
    failed: list[dict[str, str]] = Field(default_factory=list)


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    sim_iccid: str
    actor: str
    from_status: SimStatus | None
    to_status: SimStatus
    reason: str | None
    request_id: str | None
    created_at: datetime


class StatusCount(BaseModel):
    status: SimStatus
    count: int


class TopPlan(BaseModel):
    plan_id: str
    plan_name: str
    active_sims: int


class ActivationBucket(BaseModel):
    ts: datetime
    activated: int
    suspended: int


class StatsOut(BaseModel):
    total: int
    total_sims: int
    by_status: dict[str, int]
    counts_by_status: list[StatusCount]
    activations_last_24h: list[ActivationBucket]
    activations_last_24h_total: int
    mean_activation_latency_ms: float | None
    mean_activation_latency_seconds: float | None
    msisdn_pool_remaining: int
    top_plans: list[TopPlan]
