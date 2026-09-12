"""Custom exceptions and HTTP error structures for CodeImpact."""

from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Structured error payload returned to clients."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class CodeImpactException(Exception):
    """Base exception for all CodeImpact domain errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class InsufficientEvidenceException(CodeImpactException):
    """Raised when analysis cannot proceed safely due to missing evidence."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="INSUFFICIENT_EVIDENCE",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class LLMProviderException(CodeImpactException):
    """Raised when LLM communication fails or times out."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="LLM_PROVIDER_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


class MalformedLLMResponseException(CodeImpactException):
    """Raised when LLM output violates expected JSON structure."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="MALFORMED_LLM_RESPONSE",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


class CitationVerificationException(CodeImpactException):
    """Raised when citations fail validation against supplied evidence."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CITATION_VERIFICATION_FAILED",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


def register_error_handlers(app: FastAPI) -> None:
    """Register uniform JSON error handlers on the FastAPI application."""

    @app.exception_handler(CodeImpactException)
    async def codeimpact_exception_handler(request: Request, exc: CodeImpactException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Check server logs for details.",
                    "details": {},
                }
            },
        )
