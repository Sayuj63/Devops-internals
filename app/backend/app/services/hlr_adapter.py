from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings, get_settings
from app.exceptions import HlrProvisioningError
from app.metrics import hlr_calls_total

log = structlog.get_logger("hlr")


@dataclass(slots=True)
class HlrResult:
    provisioning_ref: str
    latency_ms: float


class HlrClient(Protocol):
    async def provision(self, iccid: str, imsi: str, msisdn: str) -> HlrResult: ...
    async def deprovision(self, iccid: str) -> None: ...


class HttpHlrClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = httpx.AsyncClient(
            base_url=self._settings.hlr_base_url,
            timeout=self._settings.hlr_timeout_seconds,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def provision(self, iccid: str, imsi: str, msisdn: str) -> HlrResult:
        payload = {"iccid": iccid, "imsi": imsi, "msisdn": msisdn}
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._settings.hlr_max_retries),
                wait=wait_exponential(multiplier=0.1, min=0.1, max=1.0),
                retry=retry_if_exception_type(
                    (httpx.TransportError, HlrProvisioningError)
                ),
                reraise=True,
            ):
                with attempt:
                    resp = await self._client.post("/hlr/provision", json=payload)
                    if resp.status_code >= 500:
                        hlr_calls_total.labels(outcome="server_error").inc()
                        raise HlrProvisioningError(
                            f"HLR returned {resp.status_code}: {resp.text[:200]}"
                        )
                    if resp.status_code >= 400:
                        hlr_calls_total.labels(outcome="client_error").inc()
                        raise HlrProvisioningError(
                            f"HLR rejected request ({resp.status_code}): {resp.text[:200]}"
                        )
                    body = resp.json()
                    hlr_calls_total.labels(outcome="success").inc()
                    return HlrResult(
                        provisioning_ref=body["provisioning_ref"],
                        latency_ms=float(body.get("latency_ms", 0.0)),
                    )
        except RetryError as exc:  # pragma: no cover - tenacity reraises last
            hlr_calls_total.labels(outcome="retry_exhausted").inc()
            raise HlrProvisioningError("HLR retries exhausted") from exc
        except httpx.TransportError as exc:
            hlr_calls_total.labels(outcome="transport_error").inc()
            log.error("hlr_transport_error", error=str(exc))
            raise HlrProvisioningError(f"HLR transport error: {exc}") from exc

        raise HlrProvisioningError("HLR provisioning failed")  # pragma: no cover

    async def deprovision(self, iccid: str) -> None:
        try:
            resp = await self._client.post("/hlr/deprovision", json={"iccid": iccid})
            if resp.status_code >= 400:
                hlr_calls_total.labels(outcome="deprov_error").inc()
                raise HlrProvisioningError(
                    f"HLR deprovision failed ({resp.status_code})"
                )
            hlr_calls_total.labels(outcome="deprov_success").inc()
        except httpx.TransportError as exc:
            hlr_calls_total.labels(outcome="transport_error").inc()
            raise HlrProvisioningError(str(exc)) from exc


class FakeHlrClient:
    # Used by tests so we don't need the sidecar running.
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self.deprovisioned: list[str] = []

    async def provision(self, iccid: str, imsi: str, msisdn: str) -> HlrResult:
        self.calls.append((iccid, imsi, msisdn))
        hlr_calls_total.labels(outcome="success").inc()
        return HlrResult(provisioning_ref=f"fake-ref-{iccid[-6:]}", latency_ms=1.0)

    async def deprovision(self, iccid: str) -> None:
        self.deprovisioned.append(iccid)
        hlr_calls_total.labels(outcome="deprov_success").inc()


_default_client: HttpHlrClient | None = None


def get_hlr_client() -> HlrClient:
    global _default_client
    if _default_client is None:
        _default_client = HttpHlrClient()
    return _default_client


def set_hlr_client(client: HlrClient | None) -> None:
    global _default_client
    _default_client = client  # type: ignore[assignment]
