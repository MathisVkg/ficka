from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["alive", "ready"]


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
