from rag_course.domain.models import Document, DocumentMetadata, DocumentSource
from rag_course.infrastructure.chunkers.hierarchical_chunker import HierarchicalChunker


def _make_doc(content: str) -> Document:
    return Document(
        content=content,
        metadata=DocumentMetadata(source=DocumentSource.TEXT, file_path="test.txt"),
    )


def test_hierarchical_chunker_produces_child_chunks() -> None:
    chunker = HierarchicalChunker()
    doc = _make_doc("word " * 400)
    children = chunker.chunk(doc)
    assert len(children) > 0


def test_hierarchical_chunker_children_have_parent_id() -> None:
    chunker = HierarchicalChunker()
    doc = _make_doc("word " * 400)
    children = chunker.chunk(doc)
    assert all(c.metadata.parent_chunk_id is not None for c in children)


def test_hierarchical_chunker_children_are_leaf_level() -> None:
    chunker = HierarchicalChunker()
    doc = _make_doc("word " * 400)
    children = chunker.chunk(doc)
    assert all(c.metadata.hierarchy_level == 0 for c in children)


def test_hierarchical_chunker_chunk_total_is_consistent() -> None:
    chunker = HierarchicalChunker()
    doc = _make_doc("word " * 400)
    children = chunker.chunk(doc)
    total = len(children)
    assert all(c.metadata.chunk_total == total for c in children)


def test_chunk_with_parents_returns_two_levels() -> None:
    chunker = HierarchicalChunker()
    doc = _make_doc("word " * 400)
    parents, children = chunker.chunk_with_parents(doc)

    assert len(parents) >= 1
    assert len(children) >= len(parents)
    assert all(p.metadata.hierarchy_level == 1 for p in parents)
    assert all(c.metadata.hierarchy_level == 0 for c in children)


def test_chunk_with_parents_children_reference_valid_parent_ids() -> None:
    chunker = HierarchicalChunker()
    doc = _make_doc("word " * 400)
    parents, children = chunker.chunk_with_parents(doc)

    parent_ids = {p.id for p in parents}
    assert all(c.metadata.parent_chunk_id in parent_ids for c in children)
