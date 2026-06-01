# src/rag_course/domain/models.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class DocumentSource(str, Enum):
    """Fuente de origen de un documento."""

    PDF = "pdf"
    TEXT = "text"
    WEB = "web"


class DocumentMetadata(BaseModel):
    """Metadatos asociados a un documento fuente."""

    source: DocumentSource
    file_path: str
    page_number: int | None = None
    total_pages: int | None = None
    author: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    extra: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Entidad central: un documento tal como se ingesta."""

    id: UUID = Field(default_factory=uuid4)
    content: str
    metadata: DocumentMetadata

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El contenido del documento no puede estar vacío.")
        return v.strip()


class ChunkMetadata(BaseModel):
    """Metadatos de un fragmento (chunk) derivado de un documento."""

    document_id: UUID
    chunk_index: int
    chunk_total: int
    parent_chunk_id: UUID | None = None  # Para chunking jerárquico
    hierarchy_level: int = 0  # 0 = hoja, 1 = padre, 2 = abuelo…
    start_char: int | None = None
    end_char: int | None = None
    source: DocumentSource
    file_path: str


class Chunk(BaseModel):
    """Un fragmento de documento listo para embeber e indexar."""

    id: UUID = Field(default_factory=uuid4)
    content: str
    metadata: ChunkMetadata
    embedding: list[float] | None = None  # Se añade tras el embedding


class QueryResult(BaseModel):
    """Resultado de una consulta RAG."""

    query: str
    answer: str
    source_chunks: list[Chunk]
    model_used: str
    tokens_used: int | None = None
    latency_ms: float | None = None
