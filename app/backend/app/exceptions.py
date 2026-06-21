from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class DomainError(Exception):
    status_code: int = 400
    type_uri: str = "about:blank"
    title: str = "Bad Request"

    def __init__(self, detail: str, **extra: Any) -> None:
        super().__init__(detail)
        self.detail = detail
        self.extra = extra


class SimNotFound(DomainError):
    status_code = 404
    type_uri = "https://errors.sim-prov/sim-not-found"
    title = "SIM not found"


class PlanNotFound(DomainError):
    status_code = 404
    type_uri = "https://errors.sim-prov/plan-not-found"
    title = "Plan not found"


class InvalidTransition(DomainError):
    status_code = 409
    type_uri = "https://errors.sim-prov/invalid-transition"
    title = "Invalid SIM state transition"


class MsisdnPoolExhausted(DomainError):
    status_code = 503
    type_uri = "https://errors.sim-prov/msisdn-pool-exhausted"
    title = "MSISDN pool exhausted"


class HlrProvisioningError(DomainError):
    status_code = 502
    type_uri = "https://errors.sim-prov/hlr-failure"
    title = "HLR/HSS provisioning failed"


class InvalidIccid(DomainError):
    status_code = 422
    type_uri = "https://errors.sim-prov/invalid-iccid"
    title = "Invalid ICCID"


def _problem(
    request: Request,
    status: int,
    title: str,
    detail: str,
    type_uri: str,
    **extra: Any,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": str(request.url.path),
    }
    body.update({k: v for k, v in extra.items() if v is not None})
    rid = getattr(request.state, "request_id", None)
    if rid:
        body["request_id"] = rid
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_handler(request: Request, exc: DomainError) -> JSONResponse:
        return _problem(
            request,
            exc.status_code,
            exc.title,
            exc.detail,
            exc.type_uri,
            **exc.extra,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _problem(
            request,
            422,
            "Validation error",
            "One or more fields failed validation.",
            "https://errors.sim-prov/validation",
            errors=exc.errors(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return _problem(
            request,
            exc.status_code,
            exc.detail if isinstance(exc.detail, str) else "HTTP error",
            str(exc.detail),
            "about:blank",
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        return _problem(
            request,
            500,
            "Internal server error",
            "An unexpected error occurred.",
            "https://errors.sim-prov/internal",
        )
