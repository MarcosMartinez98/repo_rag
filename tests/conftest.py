"""
Shared pytest fixtures and session-wide configuration.

The COHERE_API_KEY env var must be set before pydantic-settings imports
rag_course.config.settings (which instantiates Settings() at module level).
We set a dummy value here so unit tests never need a real API key.
"""

import os

os.environ.setdefault("COHERE_API_KEY", "test-key-for-unit-tests")

import pytest  # noqa: E402

from rag_course.domain.models import (  # noqa: E402
    Chunk,
    ChunkMetadata,
    Document,
    DocumentMetadata,
    DocumentSource,
    QueryResult,
)


@pytest.fixture
def doc_metadata() -> DocumentMetadata:
    return DocumentMetadata(source=DocumentSource.TEXT, file_path="test.txt")


@pytest.fixture
def sample_document(doc_metadata: DocumentMetadata) -> Document:
    return Document(
        content="This is sample content used in unit tests.",
        metadata=doc_metadata,
    )


@pytest.fixture
def sample_chunk(sample_document: Document) -> Chunk:
    meta = ChunkMetadata(
        document_id=sample_document.id,
        chunk_index=0,
        chunk_total=1,
        source=DocumentSource.TEXT,
        file_path="test.txt",
    )
    return Chunk(content=sample_document.content, metadata=meta)


@pytest.fixture
def sample_query_result(sample_chunk: Chunk) -> QueryResult:
    return QueryResult(
        query="What is this?",
        answer="It is sample content.",
        source_chunks=[sample_chunk],
        model_used="command-r-plus-08-2024",
    )
