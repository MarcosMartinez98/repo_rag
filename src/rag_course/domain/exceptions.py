class RagCourseError(Exception):
    """Base domain error."""


class DocumentParseError(RagCourseError):
    """Raised when a document cannot be parsed."""


class EmbeddingError(RagCourseError):
    """Raised when embedding generation fails."""


class VectorStoreError(RagCourseError):
    """Raised when an operation on the vector store fails."""


class LLMError(RagCourseError):
    """Raised when the LLM fails to generate a response."""


class ChunkingError(RagCourseError):
    """Raised when document chunking fails."""
