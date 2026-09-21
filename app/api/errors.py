from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import (
    AuthenticationFailed,
    CheckInNotFound,
    DomainError,
    EmailAlreadyExists,
    FaceEmbeddingFailed,
    FaceProfileNotFound,
    InvalidEmail,
    InvalidImage,
    InvalidToken,
    MultipleFacesDetected,
    NoFaceDetected,
    UnmatchedFace,
    UserNotFound,
)

_BAD_REQUEST_ERRORS = (EmailAlreadyExists, InvalidEmail, InvalidImage)
_NOT_FOUND_ERRORS = (CheckInNotFound, FaceProfileNotFound, UnmatchedFace, UserNotFound)
_UNPROCESSABLE_ERRORS = (FaceEmbeddingFailed, MultipleFacesDetected, NoFaceDetected)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        status_code = _status_code(exc)
        body: dict[str, Any] = {
            "detail": str(exc),
            "error": type(exc).__name__,
        }
        record_id = getattr(exc, "record_id", None)
        if record_id is not None:
            body["record_id"] = record_id
        if isinstance(exc, UnmatchedFace):
            body["best_score"] = exc.best_score
        headers = (
            {"WWW-Authenticate": "Bearer"}
            if isinstance(exc, (AuthenticationFailed, InvalidToken))
            else None
        )
        return JSONResponse(status_code=status_code, content=body, headers=headers)


def _status_code(exc: DomainError) -> int:
    if isinstance(exc, (AuthenticationFailed, InvalidToken)):
        return 401
    if isinstance(exc, _BAD_REQUEST_ERRORS):
        return 400
    if isinstance(exc, _NOT_FOUND_ERRORS):
        return 404
    if isinstance(exc, _UNPROCESSABLE_ERRORS):
        return 422
    return 400
