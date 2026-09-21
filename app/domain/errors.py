class DomainError(Exception):
    """Base class for expected business errors."""


class InvalidImage(DomainError):
    """Raised when uploaded bytes cannot be decoded as an image."""


class NoFaceDetected(DomainError):
    """Raised when an image does not contain a detectable face."""


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
