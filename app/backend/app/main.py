from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from sqlalchemy import text
from starlette.responses import Response

from app.config import get_settings
from app.db import SessionLocal, engine
from app.exceptions import register_exception_handlers
from app.middleware import RequestContextMiddleware, configure_logging
from app.routers import audit as audit_router
from app.routers import plans as plans_router
from app.routers import sims as sims_router
from app.routers import stats as stats_router
from app.services.msisdn_pool import MsisdnPool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log = structlog.get_logger("startup")
    log.info("app_starting", env=get_settings().env)
    # Warm the pool gauge on startup so /metrics is meaningful immediately.
    try:
        async with SessionLocal() as session:
            await MsisdnPool(session).refresh_gauge()
    except Exception as exc:  # pragma: no cover - bootstrap path
        log.warning("pool_gauge_warmup_failed", error=str(exc))
    yield
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
