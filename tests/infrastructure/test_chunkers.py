from unittest.mock import MagicMock

from rag_course.domain.models import Document, DocumentMetadata, DocumentSource
from rag_course.infrastructure.chunkers.recursive_chunker import RecursiveChunker


def _make_settings(chunk_size: int = 100, chunk_overlap: int = 10) -> MagicMock:
    s = MagicMock()
    s.chunk_size = chunk_size
    s.chunk_overlap = chunk_overlap
    return s


def _make_doc(content: str) -> Document:
    return Document(
        content=content,
        metadata=DocumentMetadata(source=DocumentSource.TEXT, file_path="test.txt"),
    )


def test_recursive_chunker_splits_long_document() -> None:
    chunker = RecursiveChunker(_make_settings(chunk_size=100, chunk_overlap=10))
    doc = _make_doc("word " * 200)
    chunks = chunker.chunk(doc)
    assert len(chunks) > 1


def test_recursive_chunker_short_document_produces_one_chunk() -> None:
    chunker = RecursiveChunker(_make_settings(chunk_size=500, chunk_overlap=0))
    doc = _make_doc("short content")
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1


def test_recursive_chunker_preserves_document_id() -> None:
    chunker = RecursiveChunker(_make_settings(chunk_size=100, chunk_overlap=10))
    doc = _make_doc("word " * 200)
    chunks = chunker.chunk(doc)
    assert all(c.metadata.document_id == doc.id for c in chunks)


def test_recursive_chunker_chunk_indices_are_sequential() -> None:
    chunker = RecursiveChunker(_make_settings(chunk_size=100, chunk_overlap=10))
    doc = _make_doc("word " * 200)
    chunks = chunker.chunk(doc)
    indices = [c.metadata.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))
