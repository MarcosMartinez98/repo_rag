from unittest.mock import MagicMock

import pytest

from rag_course.application.ingest_use_case import IngestUseCase
from rag_course.domain.models import Document, DocumentMetadata, DocumentSource


def _make_doc() -> Document:
    return Document(
        content="Some ingested content.",
        metadata=DocumentMetadata(source=DocumentSource.TEXT, file_path="file.txt"),
    )


def test_ingest_returns_stats_for_single_file(sample_chunk: object) -> None:
    parser = MagicMock()
    parser.parse.return_value = [_make_doc()]

    chunker = MagicMock()
    chunker.chunk.return_value = [sample_chunk]

    vector_store = MagicMock()

    use_case = IngestUseCase(parser, chunker, vector_store)
    result = use_case.execute(["file.txt"])

    assert result["files_processed"] == 1
    assert result["documents_processed"] == 1
    assert result["chunks_indexed"] == 1
    vector_store.add.assert_called_once()


def test_ingest_multiple_files_accumulates_chunks(sample_chunk: object) -> None:
    parser = MagicMock()
    parser.parse.return_value = [_make_doc()]

    chunker = MagicMock()
    chunker.chunk.return_value = [sample_chunk, sample_chunk]

    vector_store = MagicMock()

    use_case = IngestUseCase(parser, chunker, vector_store)
    result = use_case.execute(["a.txt", "b.txt"])

    assert result["files_processed"] == 2
    assert result["chunks_indexed"] == 4  # 2 files × 2 chunks each


def test_ingest_empty_file_list_skips_store() -> None:
    parser = MagicMock()
    chunker = MagicMock()
    vector_store = MagicMock()

    use_case = IngestUseCase(parser, chunker, vector_store)
    result = use_case.execute([])

    assert result["chunks_indexed"] == 0
    vector_store.add.assert_not_called()


def test_ingest_propagates_parser_error() -> None:
    parser = MagicMock()
    parser.parse.side_effect = RuntimeError("disk error")

    use_case = IngestUseCase(parser, MagicMock(), MagicMock())

    with pytest.raises(RuntimeError, match="disk error"):
        use_case.execute(["bad.txt"])
