from __future__ import annotations

import asyncio
import os
import random
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///file:simtest_shared?mode=memory&cache=shared&uri=true",
)
os.environ.setdefault("ENV", "test")
os.environ.setdefault("LOG_FORMAT", "pretty")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from app import db as db_module  # noqa: E402
from app.db import Base  # noqa: E402
from app.config import get_settings  # noqa: E402

get_settings.cache_clear()  # type: ignore[attr-defined]
db_module.rebind_engine(os.environ["DATABASE_URL"])

from app.main import create_app  # noqa: E402
from app.models import MsisdnPoolEntry, Plan, SIM, SimStatus  # noqa: E402
from app.services.hlr_adapter import FakeHlrClient, set_hlr_client  # noqa: E402
from app.seed import _gen_iccid, _gen_imsi, _gen_msisdn  # noqa: E402


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine() -> AsyncGenerator[None, None]:
    async with db_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session(db_engine):
    async with db_module.SessionLocal() as s:
        yield s


@pytest_asyncio.fixture
async def seeded(session) -> dict[str, object]:
    rng = random.Random(42)
    plan = Plan(
        name="Test Plan", data_gb=10, voice_min=500, sms_count=500, monthly_inr=199
    )
    session.add(plan)
    await session.flush()

    sims: list[SIM] = []
    seen: set[str] = set()
    while len(sims) < 10:
        iccid = _gen_iccid(rng)
        if iccid in seen:
            continue
        seen.add(iccid)
        sims.append(
            SIM(
                iccid=iccid,
                imsi=_gen_imsi(rng, len(sims) + 1),
                plan_id=plan.id,
                status=SimStatus.PENDING,
            )
        )
    for s in sims:
        session.add(s)

    for i in range(5):
        session.add(MsisdnPoolEntry(msisdn=_gen_msisdn(i), is_used=False))

    await session.commit()
    return {"plan": plan, "sims": sims}


@pytest.fixture
def fake_hlr() -> FakeHlrClient:
    client = FakeHlrClient()
    set_hlr_client(client)
    yield client
    set_hlr_client(None)


@pytest.fixture
def app(fake_hlr):
    return create_app()


@pytest_asyncio.fixture
async def client(app, db_engine):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
