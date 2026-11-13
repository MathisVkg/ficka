import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

logger = logging.getLogger("ficka")


def error_response(
    request: Request, status: int, code: str, message: str, fields: dict | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        headers={"X-Request-ID": request.state.request_id},
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request.state.request_id,
                **({"fields": fields} if fields else {}),
            }
        },
    )


def register_errors(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code = {503: "service_unavailable", 422: "validation_error", 409: "conflict"}.get(
            exc.status_code,
            "http_error",
        )
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        return error_response(
            request, exc.status_code, code, detail["message"], detail.get("fields")
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            request,
            422,
            "validation_error",
            "Check the highlighted values",
            {
                ".".join(map(str, error["loc"][1:])) or "form": error["msg"]
                for error in exc.errors()
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled request error request_id=%s", request.state.request_id)
        return error_response(request, 500, "internal_error", "An unexpected error occurred")
