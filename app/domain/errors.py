class DomainError(Exception):
    """Base class for expected business errors."""


class AuthenticationFailed(DomainError):
    """Raised when a login attempt cannot be authenticated."""

    def __init__(self) -> None:
        super().__init__("Incorrect email or password")


class InvalidToken(DomainError):
    """Raised when an access token cannot authenticate a current user."""

    def __init__(self) -> None:
        super().__init__("Could not validate credentials")


class PermissionDenied(DomainError):
    """Raised when an authenticated user cannot perform an operation."""

    def __init__(self, message: str = "You do not have permission to perform this operation"):
        super().__init__(message)


class InvalidImage(DomainError):
    """Raised when uploaded bytes cannot be decoded as an image."""


class NoFaceDetected(DomainError):
    """Raised when an image does not contain a detectable face."""

    def __init__(self, message: str = "No face was detected", *, record_id: int | None = None):
        super().__init__(message)
        self.record_id = record_id


class MultipleFacesDetected(DomainError):
    """Raised when a single-person operation receives more than one face."""


class FaceEmbeddingFailed(DomainError):
    """Raised when the model cannot produce a usable embedding."""


class EmailAlreadyExists(DomainError):
    """Raised when a normalized email address is already registered."""


class InvalidEmail(DomainError):
    """Raised when an email address is empty or structurally invalid."""


class UserNotFound(DomainError):
    """Raised when a user identifier does not exist."""


class FaceProfileNotFound(DomainError):
    """Raised when a face profile identifier does not exist."""


class UnmatchedFace(DomainError):
    """Raised after recording a check-in whose best score is below threshold."""

    def __init__(self, best_score: float | None, *, record_id: int | None = None):
        super().__init__("No registered face matched the image")
        self.best_score = best_score
        self.record_id = record_id


class CheckInNotFound(DomainError):
    """Raised when a check-in record identifier does not exist."""
