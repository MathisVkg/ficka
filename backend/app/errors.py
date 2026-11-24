"""One error format for every 4xx the API produces on purpose.

    {"error": {"code": "validation_error", "fields": {"lines.0.net_cents": "…"}}}

Services raise `AppError` subclasses; `install_error_handlers()` turns them, FastAPI's
`HTTPException`s and Pydantic's request validation errors into that format.
`fields` uses dotted paths that match the request body (`lines.0.vat_rate_bp`).
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
}


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(
        self,
        message: str,
        fields: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.fields = fields or {}
        self.extra = extra or {}


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_error"


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


def error_body(
    code: str,
    message: str,
    fields: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message, "fields": fields or {}}
    if extra:
        error.update(extra)
    return {"error": error}


def field_path(loc: tuple[Any, ...] | list[Any]) -> str:
    """('body', 'lines', 0, 'net_cents') -> 'lines.0.net_cents'."""
    parts = [str(part) for part in loc]
    if parts and parts[0] in {"body", "query", "path", "header", "cookie"}:
        parts = parts[1:]
    return ".".join(parts) or "_"


def _validation_message(error: dict[str, Any]) -> str:
    message = str(error.get("msg", "Invalid value"))
    # Pydantic prefixes custom ValueError messages with "Value error, ".
    return message.removeprefix("Value error, ")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            error_body(exc.code, exc.message, exc.fields, exc.extra), status_code=exc.status_code
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for error in exc.errors():
            fields.setdefault(field_path(error.get("loc", ())), _validation_message(error))
        return JSONResponse(
            error_body("validation_error", "Some fields are invalid.", fields), status_code=422
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = STATUS_CODES.get(exc.status_code, "error")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            error_body(code, message),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )
