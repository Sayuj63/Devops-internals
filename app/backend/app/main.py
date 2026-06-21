from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from sqlalchemy import func, select, text
from starlette.responses import Response

from app.config import get_settings
from app.db import SessionLocal, engine
from app.exceptions import register_exception_handlers
from app.metrics import sim_count_by_status
from app.middleware import RequestContextMiddleware, configure_logging
from app.models import SIM, SimStatus
from app.routers import audit as audit_router
from app.routers import plans as plans_router
from app.routers import sims as sims_router
from app.routers import stats as stats_router
from app.services.msisdn_pool import MsisdnPool


async def _refresh_sim_status_gauge() -> None:
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(SIM.status, func.count(SIM.iccid)).group_by(SIM.status)
            )
        ).all()
    seen: set[str] = set()
    for status, count in rows:
        label = status.value if hasattr(status, "value") else str(status)
        sim_count_by_status.labels(status=label).set(count)
        seen.add(label)
    # Make sure every possible status appears even when count is zero so
    # Grafana panels don't go "No data" on idle buckets.
    for st in SimStatus:
        if st.value not in seen:
            sim_count_by_status.labels(status=st.value).set(0)


async def _sim_status_gauge_loop(log: structlog.stdlib.BoundLogger) -> None:
    while True:
        try:
            await _refresh_sim_status_gauge()
        except Exception as exc:  # pragma: no cover - background task
            log.warning("sim_count_gauge_refresh_failed", error=str(exc))
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log = structlog.get_logger("startup")
    log.info("app_starting", env=get_settings().env)
    try:
        async with SessionLocal() as session:
            await MsisdnPool(session).refresh_gauge()
        await _refresh_sim_status_gauge()
    except Exception as exc:  # pragma: no cover - bootstrap path
        log.warning("pool_gauge_warmup_failed", error=str(exc))
    bg = asyncio.create_task(_sim_status_gauge_loop(log))
    try:
        yield
    finally:
        bg.cancel()
        with suppress(asyncio.CancelledError):
            await bg
        await engine.dispose()
        log.info("app_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SIM Provisioning Automation Platform",
        version="0.1.0",
        description="Operator API for managing SIM lifecycle, MSISDN pool and HLR provisioning.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[settings.request_id_header],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(plans_router.router)
    app.include_router(sims_router.router)
    app.include_router(stats_router.router)
    app.include_router(audit_router.router)

    # We expose Prometheus metrics directly via prometheus_client rather than
    # through prometheus-fastapi-instrumentator — recent FastAPI versions ship
    # an _IncludedRouter type that the instrumentator's route matcher cannot
    # handle, which would otherwise 500 every request.
    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["meta"])
    async def readyz() -> dict[str, str]:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"service": settings.app_name, "version": "0.1.0"}

    return app


app = create_app()
