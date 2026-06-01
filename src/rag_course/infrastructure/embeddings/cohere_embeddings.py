# src/rag_course/infrastructure/embeddings/cohere_embeddings.py
import cohere

from rag_course.config.settings import settings
from rag_course.domain.models import Chunk
from rag_course.domain.ports import IEmbedder


class CohereEmbedder(IEmbedder):
    """
    Genera embeddings usando la API de Cohere.

    Cohere distingue entre:
    - input_type="search_document": para indexar chunks
    - input_type="search_query": para embeber la query del usuario
    Esto es importante para la calidad de la búsqueda.
    """

    def __init__(self) -> None:
        self._client = cohere.Client(api_key=settings.cohere_api_key.get_secret_value())
        self._model = settings.cohere_embed_model

    def embed(self, chunks: list[Chunk]) -> list[Chunk]:
        """Añade embeddings a cada chunk in-place y devuelve la lista."""
        texts = [chunk.content for chunk in chunks]

        response = self._client.embed(
            texts=texts,
            model=self._model,
            input_type="search_document",
            embedding_types=["float"],
        )

        embeddings: list[list[float]] = response.embeddings.float

        # Pydantic v2: model_copy(update=...) es la forma inmutable
        return [
            chunk.model_copy(update={"embedding": embedding})
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]

    def embed_query(self, query: str) -> list[float]:
        """Embebe una query de usuario (input_type diferente)."""
        response = self._client.embed(
            texts=[query],
            model=self._model,
            input_type="search_query",
            embedding_types=["float"],
        )
        return response.embeddings.float[0]  # type: ignore
