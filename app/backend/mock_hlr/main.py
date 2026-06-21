from __future__ import annotations

import asyncio
import os
import random
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class ProvisionRequest(BaseModel):
    iccid: str = Field(min_length=19, max_length=20)
    imsi: str = Field(min_length=15, max_length=15)
    msisdn: str = Field(min_length=8, max_length=16)


class ProvisionResponse(BaseModel):
    provisioning_ref: str
    latency_ms: float
    iccid: str
    msisdn: str


class DeprovisionRequest(BaseModel):
    iccid: str


FAILURE_RATE = float(os.getenv("HLR_FAILURE_RATE", "0.05"))
MIN_LATENCY_MS = float(os.getenv("HLR_MIN_LATENCY_MS", "50"))
MAX_LATENCY_MS = float(os.getenv("HLR_MAX_LATENCY_MS", "200"))

_rng = random.Random()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(
    title="Mock HLR/HSS",
    version="0.1.0",
    description="Fake HLR/HSS endpoint that fakes provisioning latency and failure rate.",
    lifespan=lifespan,
)


async def _simulate_latency() -> float:
    delay_ms = _rng.uniform(MIN_LATENCY_MS, MAX_LATENCY_MS)
    await asyncio.sleep(delay_ms / 1000.0)
    return delay_ms


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/hlr/provision", response_model=ProvisionResponse)
async def provision(req: ProvisionRequest) -> ProvisionResponse:
    started = time.perf_counter()
    await _simulate_latency()
    if _rng.random() < FAILURE_RATE:
        raise HTTPException(status_code=503, detail="HLR transient failure")
    ref = f"HLR-{uuid.uuid4().hex[:16].upper()}"
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return ProvisionResponse(
        provisioning_ref=ref,
        latency_ms=round(elapsed_ms, 2),
        iccid=req.iccid,
        msisdn=req.msisdn,
    )


@app.post("/hlr/deprovision")
async def deprovision(req: DeprovisionRequest) -> dict[str, str]:
    await _simulate_latency()
    if _rng.random() < FAILURE_RATE / 2:
        raise HTTPException(status_code=503, detail="HLR transient failure")
    return {"status": "deprovisioned", "iccid": req.iccid}
