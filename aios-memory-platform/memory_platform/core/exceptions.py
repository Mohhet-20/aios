"""Exception hierarchy for the Memory & Knowledge Platform."""
from __future__ import annotations


class MemoryPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(MemoryPlatformError):
    pass


class ValidationError(MemoryPlatformError):
    pass


class ConflictError(MemoryPlatformError):
    pass


class ConcurrentModificationError(MemoryPlatformError):
    pass


class AuthorizationError(MemoryPlatformError):
    pass


class InvalidTransitionError(MemoryPlatformError):
    """Raised on an illegal memory/knowledge-item lifecycle transition."""


class RetentionPolicyViolationError(MemoryPlatformError):
    """Raised when an operation would violate a configured retention policy."""


class DocumentProcessingError(MemoryPlatformError):
    """Raised when document extraction/chunking/classification fails in a
    way the caller needs to know about (not silently swallowed)."""


class UnsupportedDocumentTypeError(DocumentProcessingError):
    pass


class EmbeddingDimensionMismatchError(MemoryPlatformError):
    """Raised when vectors for the same index have inconsistent dimensions —
    an index-health problem that must never be silently accepted."""


class TokenBudgetExceededError(MemoryPlatformError):
    """Raised when context assembly cannot fit required content within the
    configured token budget even after compression."""


class GraphCycleError(MemoryPlatformError):
    """Raised when a knowledge-graph relationship would create an illegal
    cycle for a relationship type that must be acyclic (e.g. 'part_of')."""
