# src/rag_course/infrastructure/retriever/multi_query_retriever.py
"""
Multi-query retriever: genera variaciones de la query original
para aumentar el recall, luego deduplica y reordena con Cohere.
"""

from langchain_cohere import ChatCohere
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from rag_course.config.settings import settings
from rag_course.domain.models import Chunk
from rag_course.domain.ports import IRetriever, IVectorStore

QUERY_EXPANSION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Genera {n_variants} variaciones de la siguiente pregunta
para buscar en una base de conocimiento. Cada variación en una línea.
Solo las variaciones, sin numeración ni explicación.""",
        ),
        ("human", "{question}"),
    ]
)


class MultiQueryRetriever(IRetriever):
    """
    Expande la query original, busca con cada variación,
    deduplica por ID de chunk y reordena con Cohere Rerank.
    """

    def __init__(self, vector_store: IVectorStore, n_variants: int = 3) -> None:
        self._store = vector_store
        self._n = n_variants
        self._llm = ChatCohere(
            cohere_api_key=settings.cohere_api_key.get_secret_value(),
            model=settings.cohere_llm_model,
        )
        self._expansion_chain = QUERY_EXPANSION_PROMPT | self._llm | StrOutputParser()

    def retrieve(self, query: str, top_k: int | None = None) -> list[Chunk]:
        k = top_k or settings.top_k_rerank

        # 1. Generar variaciones
        variants_raw: str = self._expansion_chain.invoke(
            {
                "question": query,
                "n_variants": self._n,
            }
        )
        variants = [q.strip() for q in variants_raw.strip().splitlines() if q.strip()]
        all_queries = [query] + variants

        # 2. Buscar con cada variación
        seen_ids: set[str] = set()
        all_candidates: list[Chunk] = []

        for q in all_queries:
            results = self._store.search(q, top_k=settings.top_k_retrieval)
            for chunk in results:
                chunk_id = str(chunk.id)
                if chunk_id not in seen_ids:
                    seen_ids.add(chunk_id)
                    all_candidates.append(chunk)

        # 3. Reranking sobre el pool combinado
        import cohere

        client = cohere.Client(api_key=settings.cohere_api_key.get_secret_value())
        if not all_candidates:
            return []

        rerank_response = client.rerank(
            model=settings.cohere_rerank_model,
            query=query,
            documents=[c.content for c in all_candidates],
            top_n=k,
        )

        return [all_candidates[r.index] for r in rerank_response.results]
