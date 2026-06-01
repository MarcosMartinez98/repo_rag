# RAG Course

RAG system built with Domain-Driven Design (DDD), Cohere, and ChromaDB.

## Structure

```
src/rag_course/
├── domain/          # Entities, ports (interfaces), domain exceptions
├── application/     # Use cases: ingest, query, evaluate
├── infrastructure/  # Adapters: Cohere LLM, embeddings, ChromaDB, parsers, chunkers
└── config/          # Typed settings via Pydantic Settings
```

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env   # fill in your keys
```

## Usage

```python
from rag_course.config.settings import Settings
from rag_course.infrastructure.embeddings.cohere_embeddings import CohereEmbedder
from rag_course.infrastructure.vector_store.chroma_store import ChromaVectorStore
from rag_course.infrastructure.llm.cohere_llm import CohereLLM
from rag_course.infrastructure.parsers.pdf_parser import PdfParser
from rag_course.infrastructure.chunkers.recursive_chunker import RecursiveChunker
from rag_course.application.ingest_use_case import IngestUseCase
from rag_course.application.query_use_case import QueryUseCase

settings = Settings()

ingest = IngestUseCase(
    parser=PdfParser(),
    chunker=RecursiveChunker(settings),
    embedder=CohereEmbedder(settings),
    vector_store=ChromaVectorStore(settings),
)
ingest.execute("path/to/document.pdf")

query = QueryUseCase(
    embedder=CohereEmbedder(settings),
    retriever=ChromaVectorStore(settings),
    llm=CohereLLM(settings),
)
result = query.execute("What is RAG?")
print(result.answer)
```

## Tests

```bash
pytest --cov=src/rag_course
```
