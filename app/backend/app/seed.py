from __future__ import annotations

import asyncio
import random
import secrets
import sys

import structlog
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal, engine
from app.middleware import configure_logging
from app.models import MsisdnPoolEntry, Plan, SIM, SimStatus
from app.db import Base


COUNTRY_CC = "91"
MNC = "10"
MCC = "404"

PLANS_SEED = [
    {"name": "Saver 1GB", "data_gb": 1, "voice_min": 100, "sms_count": 100, "monthly_inr": 99},
    {"name": "Smart 25GB", "data_gb": 25, "voice_min": 1500, "sms_count": 3000, "monthly_inr": 299},
    {"name": "Power 100GB", "data_gb": 100, "voice_min": 5000, "sms_count": 10000, "monthly_inr": 799},
]

log = structlog.get_logger("seed")


def _luhn_checksum(payload: str) -> str:
    total = 0
    for i, ch in enumerate(reversed(payload)):
        n = int(ch)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    check = (10 - (total % 10)) % 10
    return str(check)


def _gen_iccid(rng: random.Random) -> str:
    prefix = "8991"  # ITU-T telecom prefix.
    body = "".join(str(rng.randint(0, 9)) for _ in range(14))
    payload = prefix + body
    return payload + _luhn_checksum(payload)


def _gen_imsi(rng: random.Random, msin_counter: int) -> str:
    msin = f"{msin_counter:010d}"
    return f"{MCC}{MNC}{msin}"


def _gen_msisdn(idx: int) -> str:
    return f"+{COUNTRY_CC}{9_000_000_000 + idx}"


async def _create_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed(
    n_sims: int = 5000, n_msisdns: int = 1000, reset: bool = False
) -> None:
    configure_logging()
    await _create_schema()

    async with SessionLocal() as session:
        if reset:
            log.warning("seed_reset_requested")
            from sqlalchemy import delete

            from app.models import AuditEvent

            await session.execute(delete(AuditEvent))
            await session.execute(delete(SIM))
            await session.execute(delete(MsisdnPoolEntry))
            await session.execute(delete(Plan))
            await session.commit()

        existing_plans = (await session.execute(select(Plan))).scalars().all()
        plan_by_name = {p.name: p for p in existing_plans}
        for p in PLANS_SEED:
            if p["name"] in plan_by_name:
                continue
            plan = Plan(**p)
            session.add(plan)
            plan_by_name[p["name"]] = plan
        await session.flush()

        plans = list(plan_by_name.values())
        rng = random.Random(secrets.randbits(64))

        existing_sim_count = (
            await session.execute(select(SIM))
        ).scalars().all()
        if len(existing_sim_count) < n_sims:
            to_create = n_sims - len(existing_sim_count)
            log.info("seeding_sims", count=to_create)
            seen: set[str] = set()
            created = 0
            msin_counter = 1
            while created < to_create:
                iccid = _gen_iccid(rng)
                if iccid in seen:
                    continue
                seen.add(iccid)
                imsi = _gen_imsi(rng, msin_counter)
                msin_counter += 1
                sim = SIM(
                    iccid=iccid,
                    imsi=imsi,
                    plan_id=rng.choice(plans).id,
                    status=SimStatus.PENDING,
                )
                session.add(sim)
                created += 1
                if created % 1000 == 0:
                    await session.flush()
            await session.flush()

        existing_pool = (
            await session.execute(select(MsisdnPoolEntry))
        ).scalars().all()
        if len(existing_pool) < n_msisdns:
            base = len(existing_pool)
            log.info("seeding_msisdns", count=n_msisdns - base)
            for i in range(base, n_msisdns):
                session.add(MsisdnPoolEntry(msisdn=_gen_msisdn(i), is_used=False))
            await session.flush()

        await session.commit()
        log.info(
            "seed_complete",
            plans=len(plans),
            sims=n_sims,
            msisdns=n_msisdns,
            db_url=get_settings().database_url,
        )


def _parse_args(argv: list[str]) -> dict[str, int | bool]:
    args: dict[str, int | bool] = {"n_sims": 5000, "n_msisdns": 1000, "reset": False}
    for a in argv:
        if a == "--reset":
            args["reset"] = True
        elif a.startswith("--sims="):
            args["n_sims"] = int(a.split("=", 1)[1])
        elif a.startswith("--msisdns="):
            args["n_msisdns"] = int(a.split("=", 1)[1])
    return args


def main() -> None:
    args = _parse_args(sys.argv[1:])
    asyncio.run(
        seed(
            n_sims=int(args["n_sims"]),
            n_msisdns=int(args["n_msisdns"]),
            reset=bool(args["reset"]),
        )
    )


if __name__ == "__main__":
    main()
