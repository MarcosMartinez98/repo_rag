import pytest

from rag_course.domain.models import (
    Chunk,
    Document,
    DocumentMetadata,
    DocumentSource,
    QueryResult,
)


def test_document_content_is_stripped(doc_metadata: DocumentMetadata) -> None:
    doc = Document(content="  hello  ", metadata=doc_metadata)
    assert doc.content == "hello"


def test_document_rejects_blank_content(doc_metadata: DocumentMetadata) -> None:
    with pytest.raises(ValueError, match="no puede estar vacío"):
        Document(content="   ", metadata=doc_metadata)


def test_document_has_auto_uuid(doc_metadata: DocumentMetadata) -> None:
    doc1 = Document(content="a", metadata=doc_metadata)
    doc2 = Document(content="b", metadata=doc_metadata)
    assert doc1.id != doc2.id


def test_chunk_embedding_defaults_to_none(sample_chunk: Chunk) -> None:
    assert sample_chunk.embedding is None


def test_chunk_metadata_carries_document_id(
    sample_document: Document, sample_chunk: Chunk
) -> None:
    assert sample_chunk.metadata.document_id == sample_document.id


def test_query_result_source_chunks(sample_query_result: QueryResult) -> None:
    assert len(sample_query_result.source_chunks) == 1
    assert sample_query_result.answer == "It is sample content."


def test_document_metadata_source_enum() -> None:
    meta = DocumentMetadata(source=DocumentSource.PDF, file_path="doc.pdf")
    assert meta.source == DocumentSource.PDF
    assert meta.page_number is None
