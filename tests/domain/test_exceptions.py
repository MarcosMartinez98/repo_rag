import pytest

from rag_course.domain.exceptions import (
    ChunkingError,
    DocumentParseError,
    EmbeddingError,
    LLMError,
    RagCourseError,
    VectorStoreError,
)


@pytest.mark.parametrize(
    "exc_class",
    [DocumentParseError, EmbeddingError, VectorStoreError, LLMError, ChunkingError],
)
def test_domain_exceptions_are_subclass_of_base(
    exc_class: type[RagCourseError],
) -> None:
    assert issubclass(exc_class, RagCourseError)


def test_exceptions_carry_message() -> None:
    err = ChunkingError("split failed")
    assert "split failed" in str(err)


def test_domain_exceptions_are_catchable_as_base() -> None:
    with pytest.raises(RagCourseError):
        raise DocumentParseError("bad file")
