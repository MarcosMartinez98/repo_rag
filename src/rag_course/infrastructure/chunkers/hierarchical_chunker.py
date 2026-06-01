# src/rag_course/infrastructure/chunkers/hierarchical_chunker.py
"""
Chunking jerárquico: genera pares padre-hijo.
Los hijos (pequeños) se indexan para búsqueda.
Los padres (grandes) se recuperan para dar contexto al LLM.
"""

from uuid import uuid4

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_course.config.settings import settings
from rag_course.domain.models import Chunk, ChunkMetadata, Document
from rag_course.domain.ports import IChunker


class HierarchicalChunker(IChunker):
    """
    Estrategia de chunking en dos niveles:

    Nivel 0 (padre): chunks grandes, proveen contexto al LLM.
    Nivel 1 (hijo):  chunks pequeños, se indexan en el vector store.

    Cada hijo conoce a su padre via parent_chunk_id.
    """

    def __init__(self) -> None:
        # Splitter para chunks padre (grandes)
        self._parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.parent_chunk_size,
            chunk_overlap=0,  # Los padres no se solapan entre sí
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        # Splitter para chunks hijo (pequeños)
        self._child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk(self, document: Document) -> list[Chunk]:
        """
        Genera únicamente los chunks HIJO (los que se indexan).
        Los hijos llevan referencia al padre en su metadata.
        """
        parent_texts = self._parent_splitter.split_text(document.content)
        child_chunks: list[Chunk] = []
        child_global_index = 0

        for parent_text in parent_texts:
            parent_id = uuid4()
            child_texts = self._child_splitter.split_text(parent_text)

            for _child_index, child_text in enumerate(child_texts):
                meta = ChunkMetadata(
                    document_id=document.id,
                    chunk_index=child_global_index,
                    chunk_total=-1,  # Se actualiza al final
                    parent_chunk_id=parent_id,
                    hierarchy_level=0,  # 0 = hijo (el que se indexa)
                    source=document.metadata.source,
                    file_path=document.metadata.file_path,
                )
                child_chunks.append(
                    Chunk(
                        content=child_text,
                        metadata=meta,
                    )
                )
                child_global_index += 1

        # Actualizar chunk_total ahora que sabemos el total
        total = len(child_chunks)
        return [
            chunk.model_copy(
                update={
                    "metadata": chunk.metadata.model_copy(update={"chunk_total": total})
                }
            )
            for chunk in child_chunks
        ]

    def chunk_with_parents(self, document: Document) -> tuple[list[Chunk], list[Chunk]]:
        """
        Devuelve (parents, children).
        Útil si queremos guardar los padres en un store separado.
        """
        parent_texts = self._parent_splitter.split_text(document.content)
        all_parents: list[Chunk] = []
        all_children: list[Chunk] = []

        for p_idx, parent_text in enumerate(parent_texts):
            parent_id = uuid4()
            parent_chunk = Chunk(
                id=parent_id,
                content=parent_text,
                metadata=ChunkMetadata(
                    document_id=document.id,
                    chunk_index=p_idx,
                    chunk_total=len(parent_texts),
                    hierarchy_level=1,  # 1 = padre
                    source=document.metadata.source,
                    file_path=document.metadata.file_path,
                ),
            )
            all_parents.append(parent_chunk)

            child_texts = self._child_splitter.split_text(parent_text)
            for c_idx, child_text in enumerate(child_texts):
                all_children.append(
                    Chunk(
                        content=child_text,
                        metadata=ChunkMetadata(
                            document_id=document.id,
                            chunk_index=c_idx,
                            chunk_total=len(child_texts),
                            parent_chunk_id=parent_id,
                            hierarchy_level=0,
                            source=document.metadata.source,
                            file_path=document.metadata.file_path,
                        ),
                    )
                )

        return all_parents, all_children
