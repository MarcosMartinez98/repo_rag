from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_course.config.settings import Settings
from rag_course.domain.exceptions import ChunkingError
from rag_course.domain.models import Chunk, ChunkMetadata, Document
from rag_course.domain.ports import IChunker


class RecursiveChunker(IChunker):
    def __init__(self, settings: Settings) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

    def chunk(self, document: Document) -> list[Chunk]:
        try:
            texts = self._splitter.split_text(document.content)
        except Exception as exc:
            raise ChunkingError(str(exc)) from exc

        return [
            Chunk(
                content=text,
                metadata=ChunkMetadata(
                    document_id=document.id,
                    chunk_index=i,
                    chunk_total=len(texts),
                    source=document.metadata.source,
                    file_path=document.metadata.file_path,
                ),
            )
            for i, text in enumerate(texts)
        ]
