from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InvalidTransition, SimNotFound
from app.metrics import sim_activation_latency_seconds, sim_state_transitions_total
from app.models import AuditEvent, SIM, SimStatus
from app.services.hlr_adapter import HlrClient
from app.services.msisdn_pool import MsisdnPool

log = structlog.get_logger("sim_service")


VALID_TRANSITIONS: dict[SimStatus, set[SimStatus]] = {
    SimStatus.PENDING: {SimStatus.ALLOCATED, SimStatus.RECYCLED},
    SimStatus.ALLOCATED: {SimStatus.ACTIVE, SimStatus.RECYCLED},
    SimStatus.ACTIVE: {SimStatus.SUSPENDED, SimStatus.PORTED, SimStatus.RECYCLED},
    SimStatus.SUSPENDED: {SimStatus.ACTIVE, SimStatus.RECYCLED},
    SimStatus.PORTED: set(),
    SimStatus.RECYCLED: set(),
}


class SimService:
    def __init__(
        self,
        session: AsyncSession,
        hlr: HlrClient,
        msisdn_pool: MsisdnPool,
        request_id: str | None = None,
    ) -> None:
        self._session = session
        self._hlr = hlr
        self._pool = msisdn_pool
        self._request_id = request_id

    async def _load(self, iccid: str) -> SIM:
        sim = (
            await self._session.execute(select(SIM).where(SIM.iccid == iccid))
        ).scalar_one_or_none()
        if sim is None:
            raise SimNotFound(f"SIM with ICCID {iccid} not found.")
        return sim

    def _assert_transition(self, sim: SIM, target: SimStatus) -> None:
        allowed = VALID_TRANSITIONS.get(sim.status, set())
        if target not in allowed:
            raise InvalidTransition(
                f"Cannot transition {sim.iccid} from {sim.status.value} to {target.value}.",
                from_status=sim.status.value,
                to_status=target.value,
            )

    async def _record(
        self,
        sim: SIM,
        from_status: SimStatus | None,
        to_status: SimStatus,
        actor: str,
        reason: str | None,
    ) -> AuditEvent:
        evt = AuditEvent(
            sim_iccid=sim.iccid,
            actor=actor,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            request_id=self._request_id,
        )
        self._session.add(evt)
        sim.status = to_status
        sim.last_transition_at = datetime.now(timezone.utc)
        sim_state_transitions_total.labels(
            from_status=(from_status.value if from_status else "NONE"),
            to_status=to_status.value,
        ).inc()
        await self._session.flush()
        return evt

    async def allocate(
        self, iccid: str, plan_id: str | None, actor: str, reason: str | None
    ) -> SIM:
        sim = await self._load(iccid)
        self._assert_transition(sim, SimStatus.ALLOCATED)
        prior = sim.status
        if plan_id is not None:
            sim.plan_id = plan_id
        sim.allocated_at = datetime.now(timezone.utc)
        await self._record(sim, prior, SimStatus.ALLOCATED, actor, reason)
        log.info("sim_allocated", iccid=iccid, plan_id=sim.plan_id)
        return sim

    async def activate(
        self, iccid: str, actor: str, reason: str | None
    ) -> SIM:
        sim = await self._load(iccid)
        self._assert_transition(sim, SimStatus.ACTIVE)
        prior = sim.status

        if sim.msisdn is None:
            sim.msisdn = await self._pool.allocate(sim.iccid)

        hlr_result = await self._hlr.provision(sim.iccid, sim.imsi, sim.msisdn)
        sim.provisioning_ref = hlr_result.provisioning_ref

        now = datetime.now(timezone.utc)
        sim.activated_at = now
        if sim.allocated_at is not None:
            allocated = sim.allocated_at
            if allocated.tzinfo is None:
                # SQLite returns naive datetimes; coerce to UTC for math.
                allocated = allocated.replace(tzinfo=timezone.utc)
            latency = (now - allocated).total_seconds()
            if latency >= 0:
                sim_activation_latency_seconds.observe(latency)

        await self._record(sim, prior, SimStatus.ACTIVE, actor, reason)
        log.info("sim_activated", iccid=iccid, msisdn=sim.msisdn)
        return sim

    async def suspend(self, iccid: str, actor: str, reason: str | None) -> SIM:
        sim = await self._load(iccid)
        self._assert_transition(sim, SimStatus.SUSPENDED)
        prior = sim.status
        await self._record(sim, prior, SimStatus.SUSPENDED, actor, reason)
        log.info("sim_suspended", iccid=iccid)
        return sim

    async def resume(self, iccid: str, actor: str, reason: str | None) -> SIM:
        sim = await self._load(iccid)
        self._assert_transition(sim, SimStatus.ACTIVE)
        prior = sim.status
        await self._record(sim, prior, SimStatus.ACTIVE, actor, reason)
        log.info("sim_resumed", iccid=iccid)
        return sim

    async def port_out(self, iccid: str, actor: str, reason: str | None) -> SIM:
        sim = await self._load(iccid)
        self._assert_transition(sim, SimStatus.PORTED)
        prior = sim.status
        await self._hlr.deprovision(sim.iccid)
        await self._record(sim, prior, SimStatus.PORTED, actor, reason)
        log.info("sim_ported", iccid=iccid)
        return sim

    async def recycle(self, iccid: str, actor: str, reason: str | None) -> SIM:
        sim = await self._load(iccid)
        self._assert_transition(sim, SimStatus.RECYCLED)
        prior = sim.status
        if sim.msisdn is not None:
            await self._pool.release(sim.msisdn)
            sim.msisdn = None
        sim.provisioning_ref = None
        await self._record(sim, prior, SimStatus.RECYCLED, actor, reason)
        log.info("sim_recycled", iccid=iccid)
        return sim
