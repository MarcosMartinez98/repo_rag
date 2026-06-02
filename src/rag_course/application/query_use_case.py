# src/rag_course/application/query_use_case.py
"""
Caso de uso central: procesar una pregunta con RAG.
Orquesta retriever + LLM + prompt, devuelve QueryResult tipado.
"""

import time

from langchain_core.prompts import ChatPromptTemplate

from rag_course.config.settings import settings
from rag_course.domain.models import QueryResult
from rag_course.domain.ports import ILanguageModel, IRetriever

RAG_SYSTEM_PROMPT = """Eres un asistente experto. Responde la pregunta del usuario
ÚNICAMENTE basándote en los fragmentos de contexto proporcionados.
Si la respuesta no está en el contexto, di explícitamente que no tienes
esa información. No inventes datos.

Contexto:
{context}"""


class QueryUseCase:
    """
    Caso de uso: recibe una query, recupera contexto, genera respuesta.
    Depende de interfaces (puertos), nunca de implementaciones concretas.
    """

    def __init__(self, retriever: IRetriever, llm: ILanguageModel) -> None:
        self._retriever = retriever
        self._llm = llm

    def execute(self, query: str) -> QueryResult:
        start = time.perf_counter()

        # 1. Recuperar chunks relevantes
        chunks = self._retriever.retrieve(query)

        if not chunks:
            return QueryResult(
                query=query,
                answer="No encontré información relevante en los documentos.",
                source_chunks=[],
                model_used=settings.cohere_llm_model,
            )

        # 2. Construir el contexto concatenando los chunks
        context = "\n\n---\n\n".join(
            f"[Fuente: {c.metadata.file_path}, chunk {c.metadata.chunk_index}]\n{c.content}"
            for c in chunks
        )

        # 3. Construir el prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", RAG_SYSTEM_PROMPT),
                ("human", "{question}"),
            ]
        )
        filled_prompt = prompt.format_messages(context=context, question=query)
        prompt_str = "\n".join(str(m.content) for m in filled_prompt)

        # 4. Llamar al LLM
        answer = self._llm.generate(prompt_str)

        latency_ms = (time.perf_counter() - start) * 1000

        return QueryResult(
            query=query,
            answer=answer,
            source_chunks=chunks,
            model_used=settings.cohere_llm_model,
            latency_ms=round(latency_ms, 2),
        )
