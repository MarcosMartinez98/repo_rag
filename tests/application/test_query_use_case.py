from unittest.mock import MagicMock

from rag_course.application.query_use_case import QueryUseCase
from rag_course.domain.models import Chunk, QueryResult


def test_query_returns_no_info_when_retriever_empty() -> None:
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()

    result = QueryUseCase(retriever, llm).execute("what is X?")

    assert isinstance(result, QueryResult)
    assert result.source_chunks == []
    assert "No encontré" in result.answer
    llm.generate.assert_not_called()


def test_query_calls_llm_when_chunks_found(sample_chunk: Chunk) -> None:
    retriever = MagicMock()
    retriever.retrieve.return_value = [sample_chunk]

    llm = MagicMock()
    llm.generate.return_value = "The answer is 42."

    result = QueryUseCase(retriever, llm).execute("what is X?")

    llm.generate.assert_called_once()
    assert result.answer == "The answer is 42."
    assert result.source_chunks == [sample_chunk]


def test_query_result_includes_latency(sample_chunk: Chunk) -> None:
    retriever = MagicMock()
    retriever.retrieve.return_value = [sample_chunk]
    llm = MagicMock()
    llm.generate.return_value = "answer"

    result = QueryUseCase(retriever, llm).execute("q")

    assert result.latency_ms is not None
    assert result.latency_ms >= 0


def test_query_context_contains_chunk_content(sample_chunk: Chunk) -> None:
    retriever = MagicMock()
    retriever.retrieve.return_value = [sample_chunk]
    llm = MagicMock()
    llm.generate.return_value = "ok"

    QueryUseCase(retriever, llm).execute("q")

    prompt_arg: str = llm.generate.call_args[0][0]
    assert sample_chunk.content in prompt_arg
