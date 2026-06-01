# src/rag_course/infrastructure/retriever/cohere_rerank_retriever.py
import cohere

from rag_course.config.settings import settings
from rag_course.domain.models import Chunk
from rag_course.domain.ports import IRetriever, IVectorStore


class CohereReRankRetriever(IRetriever):
    """
    Retriever en dos fases:
    1. Búsqueda vectorial: obtiene top_k_retrieval candidatos.
    2. Reranking: Cohere puntúa y reordena, quedamos top_k_rerank.
    """

    def __init__(self, vector_store: IVectorStore) -> None:
        self._store = vector_store
        self._client = cohere.Client(api_key=settings.cohere_api_key.get_secret_value())
        self._rerank_model = settings.cohere_rerank_model

    def retrieve(self, query: str, top_k: int | None = None) -> list[Chunk]:
        k_rerank = top_k or settings.top_k_rerank

        # Fase 1: búsqueda vectorial (recoge más candidatos de los que necesitamos)
        candidates: list[Chunk] = self._store.search(
            query=query,
            top_k=settings.top_k_retrieval,
        )

        if not candidates:
            return []

        # Fase 2: reranking con Cohere
        rerank_response = self._client.rerank(
            model=self._rerank_model,
            query=query,
            documents=[c.content for c in candidates],
            top_n=k_rerank,
        )

        # Reordenamos los chunks según el índice devuelto por Cohere
        return [candidates[result.index] for result in rerank_response.results]
