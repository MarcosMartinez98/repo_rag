# src/rag_course/infrastructure/vector_store/chroma_store.py
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from rag_course.config.settings import settings
from rag_course.domain.models import Chunk, ChunkMetadata, DocumentSource
from rag_course.domain.ports import IVectorStore
from rag_course.infrastructure.embeddings.cohere_embeddings import CohereEmbedder


class ChromaVectorStore(IVectorStore):
    """
    Adaptador para ChromaDB como vector store persistente.
    Serializa los metadatos Pydantic a dict para ChromaDB,
    y los deserializa al recuperar, manteniendo los tipos.
    """

    def __init__(self) -> None:
        self._embedder = CohereEmbedder()
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, chunks: list[Chunk]) -> None:
        """Indexa los chunks en ChromaDB."""
        # Primero generamos los embeddings si no los tienen
        chunks_with_embeddings = self._embedder.embed(chunks)

        self._collection.add(
            ids=[str(chunk.id) for chunk in chunks_with_embeddings],
            embeddings=[chunk.embedding for chunk in chunks_with_embeddings],
            documents=[chunk.content for chunk in chunks_with_embeddings],
            metadatas=[
                self._serialize_metadata(chunk.metadata)
                for chunk in chunks_with_embeddings
            ],
        )

    def search(self, query: str, top_k: int = 5) -> list[Chunk]:
        """Busca los chunks más similares a la query."""
        query_embedding = self._embedder.embed_query(query)

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "embeddings"],
        )

        return self._parse_results(results)

    def _serialize_metadata(self, metadata: ChunkMetadata) -> dict[str, Any]:
        """
        ChromaDB solo acepta valores primitivos en metadatos.
        Serializamos UUIDs a str y enums a str.
        """
        return {
            "document_id": str(metadata.document_id),
            "chunk_index": metadata.chunk_index,
            "chunk_total": metadata.chunk_total,
            "parent_chunk_id": str(metadata.parent_chunk_id)
            if metadata.parent_chunk_id
            else "",
            "hierarchy_level": metadata.hierarchy_level,
            "start_char": metadata.start_char or -1,
            "end_char": metadata.end_char or -1,
            "source": metadata.source.value,
            "file_path": metadata.file_path,
        }

    def _parse_results(self, results: dict[str, Any]) -> list[Chunk]:
        """Reconstruye Chunks tipados desde la respuesta de ChromaDB."""
        chunks: list[Chunk] = []
        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        embeddings = (
            results["embeddings"][0] if results.get("embeddings") else [None] * len(ids)
        )

        for id_, doc, meta, emb in zip(
            ids, documents, metadatas, embeddings, strict=True
        ):
            chunk_meta = ChunkMetadata(
                document_id=meta["document_id"],
                chunk_index=meta["chunk_index"],
                chunk_total=meta["chunk_total"],
                parent_chunk_id=meta["parent_chunk_id"] or None,
                hierarchy_level=meta["hierarchy_level"],
                start_char=meta["start_char"] if meta["start_char"] != -1 else None,
                end_char=meta["end_char"] if meta["end_char"] != -1 else None,
                source=DocumentSource(meta["source"]),
                file_path=meta["file_path"],
            )
            chunks.append(
                Chunk(
                    id=id_,
                    content=doc,
                    metadata=chunk_meta,
                    embedding=emb,
                )
            )

        return chunks
