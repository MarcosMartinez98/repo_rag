"""
HTTP API layer — exposes the RAG pipeline over FastAPI.
Separates transport (HTTP) from business logic (use cases).
"""

import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from rag_course.application.ingest_use_case import IngestUseCase
from rag_course.application.query_use_case import QueryUseCase
from rag_course.infrastructure.chunkers.hierarchical_chunker import HierarchicalChunker
from rag_course.infrastructure.llm.cohere_llm import CohereLLM
from rag_course.infrastructure.parsers.pdf_parser import PdfParser
from rag_course.infrastructure.retriever.multi_query_retriever import (
    MultiQueryRetriever,
)
from rag_course.infrastructure.vector_store.chroma_store import ChromaVectorStore

_ingest_uc: IngestUseCase
_query_uc: QueryUseCase


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Wire up all dependencies once at startup — not per request."""
    global _ingest_uc, _query_uc
    store = ChromaVectorStore()
    _ingest_uc = IngestUseCase(
        parser=PdfParser(),
        chunker=HierarchicalChunker(),
        vector_store=store,
    )
    _query_uc = QueryUseCase(
        retriever=MultiQueryRetriever(vector_store=store),
        llm=CohereLLM(),
    )
    yield


app = FastAPI(
    title="RAG Course API",
    description="RAG system built with DDD architecture on Cohere + ChromaDB",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Request / Response models ──────────────────────────────────────────────────


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    model_used: str
    latency_ms: float | None
    sources: list[str]


# ── Endpoints ──────────────────────────────────────────────────────────────────


@app.get("/health")
def health() -> dict[str, str]:
    """Load balancer health check — returns 200 when the service is ready."""
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(file: UploadFile) -> dict[str, Any]:
    """
    Upload a PDF or TXT file to ingest into the vector store.
    The file is saved to a temporary path, processed, then deleted.
    """
    suffix = Path(file.filename or "upload").suffix
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        return _ingest_uc.execute([tmp_path])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    """Ask a question — returns an answer grounded in the ingested documents."""
    try:
        result = _query_uc.execute(request.question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return QueryResponse(
        question=result.query,
        answer=result.answer,
        model_used=result.model_used,
        latency_ms=result.latency_ms,
        sources=list({c.metadata.file_path for c in result.source_chunks}),
    )
