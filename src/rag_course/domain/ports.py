# src/rag_course/domain/ports.py
from abc import ABC, abstractmethod

from rag_course.domain.models import Chunk, Document


class IDocumentParser(ABC):
    """Puerto para parsear ficheros en Documents."""

    @abstractmethod
    def parse(self, file_path: str) -> list[Document]:
        """Parsea un fichero y devuelve lista de Documents."""
        ...


class IChunker(ABC):
    """Puerto para dividir Documents en Chunks."""

    @abstractmethod
    def chunk(self, document: Document) -> list[Chunk]:
        """Divide un documento en fragmentos."""
        ...


class IEmbedder(ABC):
    """Puerto para generar embeddings de Chunks."""

    @abstractmethod
    def embed(self, chunks: list[Chunk]) -> list[Chunk]:
        """Añade embeddings a los chunks y los devuelve."""
        ...


class IVectorStore(ABC):
    """Puerto para almacenar y recuperar Chunks por similitud."""

    @abstractmethod
    def add(self, chunks: list[Chunk]) -> None:
        """Añade chunks al store."""
        ...

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[Chunk]:
        """Busca los chunks más similares a una query."""
        ...


class IRetriever(ABC):
    """Puerto para el retriever (puede incluir reranking)."""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> list[Chunk]: ...


class ILanguageModel(ABC):
    """Puerto para el LLM."""

    @abstractmethod
    def generate(self, prompt: str) -> str: ...
