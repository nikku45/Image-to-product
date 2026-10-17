from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Stable machine-readable error code")
    message: str = Field(..., description="Human-readable description of the error")
    details: Optional[Any] = Field(default=None, description="Optional extra error details")


class ErrorResponse(BaseModel):
    error: ErrorDetail
