from __future__ import annotations

import pytest
from sqlalchemy import select

from app.exceptions import InvalidTransition, MsisdnPoolExhausted, SimNotFound
from app.models import AuditEvent, SimStatus
from app.services.hlr_adapter import FakeHlrClient
from app.services.msisdn_pool import MsisdnPool
from app.services.sim_service import SimService


@pytest.mark.asyncio
async def test_full_happy_path(session, seeded):
    sim = seeded["sims"][0]
    svc = SimService(
        session, FakeHlrClient(), MsisdnPool(session), request_id="req-1"
    )

    await svc.allocate(sim.iccid, plan_id=None, actor="op", reason="initial")
    assert sim.status == SimStatus.ALLOCATED
    assert sim.allocated_at is not None

    await svc.activate(sim.iccid, actor="op", reason="customer pickup")
    assert sim.status == SimStatus.ACTIVE
    assert sim.msisdn is not None
    assert sim.provisioning_ref is not None and sim.provisioning_ref.startswith("fake-ref-")
    assert sim.activated_at is not None

    await svc.suspend(sim.iccid, actor="op", reason="non-payment")
    assert sim.status == SimStatus.SUSPENDED

    await svc.resume(sim.iccid, actor="op", reason="paid")
    assert sim.status == SimStatus.ACTIVE

    await svc.port_out(sim.iccid, actor="op", reason="MNP")
    assert sim.status == SimStatus.PORTED

    events = (
        await session.execute(
            select(AuditEvent)
            .where(AuditEvent.sim_iccid == sim.iccid)
            .order_by(AuditEvent.created_at.asc())
        )
    ).scalars().all()
    assert [e.to_status for e in events] == [
        SimStatus.ALLOCATED,
        SimStatus.ACTIVE,
        SimStatus.SUSPENDED,
        SimStatus.ACTIVE,
        SimStatus.PORTED,
    ]
    assert all(e.request_id == "req-1" for e in events)


@pytest.mark.asyncio
async def test_invalid_transition_rejected(session, seeded):
    sim = seeded["sims"][1]
    svc = SimService(session, FakeHlrClient(), MsisdnPool(session))

    with pytest.raises(InvalidTransition):
        await svc.activate(sim.iccid, actor="op", reason=None)

    await svc.allocate(sim.iccid, plan_id=None, actor="op", reason=None)
    await svc.activate(sim.iccid, actor="op", reason=None)
    await svc.port_out(sim.iccid, actor="op", reason=None)

    with pytest.raises(InvalidTransition):
        await svc.suspend(sim.iccid, actor="op", reason=None)


@pytest.mark.asyncio
async def test_sim_not_found(session, seeded):
    svc = SimService(session, FakeHlrClient(), MsisdnPool(session))
    with pytest.raises(SimNotFound):
        await svc.allocate(
            "8991000000000000017", plan_id=None, actor="op", reason=None
        )


@pytest.mark.asyncio
async def test_recycle_releases_msisdn(session, seeded):
    sim = seeded["sims"][2]
    svc = SimService(session, FakeHlrClient(), MsisdnPool(session))
    await svc.allocate(sim.iccid, plan_id=None, actor="op", reason=None)
    await svc.activate(sim.iccid, actor="op", reason=None)
    msisdn = sim.msisdn
    assert msisdn is not None
    await svc.recycle(sim.iccid, actor="op", reason="lost")
    assert sim.status == SimStatus.RECYCLED
    assert sim.msisdn is None

    pool = MsisdnPool(session)
    remaining_before = await pool.remaining()
    # Allocate another SIM to verify the released MSISDN re-enters the pool.
    other = seeded["sims"][3]
    await svc.allocate(other.iccid, plan_id=None, actor="op", reason=None)
    await svc.activate(other.iccid, actor="op", reason=None)
    remaining_after = await pool.remaining()
    assert remaining_after == remaining_before - 1


@pytest.mark.asyncio
async def test_msisdn_pool_exhausted(session, seeded):
    svc = SimService(session, FakeHlrClient(), MsisdnPool(session))
    activated = 0
    exhausted_iccid: str | None = None
    for sim in seeded["sims"]:
        await svc.allocate(sim.iccid, plan_id=None, actor="op", reason=None)
        try:
            await svc.activate(sim.iccid, actor="op", reason=None)
            activated += 1
        except MsisdnPoolExhausted:
            exhausted_iccid = sim.iccid
            break
    assert activated == 5  # seeded with 5 MSISDNs
    assert exhausted_iccid is not None
    # The SIM that hit exhaustion is ALLOCATED — re-attempting must still 503.
    with pytest.raises(MsisdnPoolExhausted):
        await svc.activate(exhausted_iccid, actor="op", reason=None)
