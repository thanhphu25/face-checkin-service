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
