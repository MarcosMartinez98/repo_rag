# CLAUDE.md — RAG Course Project

## Project Overview

Production-grade Retrieval-Augmented Generation (RAG) system built with Domain-Driven Design (DDD) architecture. Combines Cohere's LLM, embeddings, and reranking with ChromaDB for vector storage to enable intelligent document querying over PDFs and text files.

- **Language**: Python 3.11–3.13
- **Package manager**: Poetry
- **Container runtime**: Podman / Docker
- **Deployment target**: AWS EC2 (free tier), with ECR for images

---

## Architecture

The project enforces strict **Ports & Adapters (Hexagonal Architecture)**. The domain is pure Python with no external dependencies; all external calls go through abstract interfaces defined in `ports.py`.

```
src/rag_course/
├── domain/              # Pure business logic — no external deps allowed
│   ├── models.py        # Pydantic entities: Document, Chunk, QueryResult
│   ├── ports.py         # Abstract interfaces (IDocumentParser, IChunker, IEmbedder, IVectorStore, IRetriever, ILanguageModel)
│   └── exceptions.py    # Exception hierarchy rooted at RagCourseError
├── application/         # Use cases — orchestrate domain + infrastructure
│   ├── ingest_use_case.py       # Parse → Chunk → Embed → Store
│   ├── query_use_case.py        # Retrieve → Rerank → LLM generation
│   └── evaluate_use_case.py     # RAGAS evaluation (requires optional extras)
├── infrastructure/      # Concrete adapter implementations
│   ├── parsers/         # PdfParser (pdfminer.six), TextParser
│   ├── chunkers/        # RecursiveChunker (LangChain), HierarchicalChunker
│   ├── embeddings/      # CohereEmbedder (embed-multilingual-v3.0)
│   ├── llm/             # CohereLLM (command-r-plus-08-2024)
│   ├── vector_store/    # ChromaVectorStore (persistent, cosine similarity)
│   └── retriever/       # CohereReRankRetriever, MultiQueryRetriever
├── config/
│   └── settings.py      # Pydantic Settings — all config loaded from .env
├── api.py               # FastAPI application and HTTP endpoints
└── cli.py               # Typer CLI for command-line usage
```

### Key design rules
- Domain (`domain/`) **never imports** from `infrastructure/`, `application/`, `api.py`, or any external library.
- Application layer depends only on domain interfaces (ports), never on concrete adapters.
- Adapters depend on domain models, never on each other.
- All settings flow through `config/settings.py`; no raw `os.environ` calls elsewhere.

---

## Data Flow

### Ingestion
```
File (PDF/TXT)
  → Parser          (page-by-page for PDFs, preserves page metadata)
  → Document list
  → Chunker         (RecursiveChunker or HierarchicalChunker)
  → Chunk list
  → CohereEmbedder  (input_type="search_document", batched)
  → Chunk list with embeddings
  → ChromaVectorStore.add()
```

### Query
```
User question
  → MultiQueryRetriever  (expands to N query variants via ChatCohere)
  → ChromaVectorStore.search() per variant  (top_k_retrieval candidates each)
  → Deduplicate by chunk ID
  → Cohere Rerank        (rerank-multilingual-v3.0, returns top_k_rerank)
  → QueryUseCase         (builds RAG prompt: question + chunk context)
  → CohereLLM.generate() (command-r-plus-08-2024)
  → QueryResult          (answer + source_chunks + latency_ms)
```

---

## Configuration

Copy `.env.example` to `.env` and fill in values before running anything.

| Setting | Default | Description |
|---|---|---|
| `COHERE_API_KEY` | required | Cohere API key (stored as SecretStr, never logged) |
| `COHERE_LLM_MODEL` | `command-r-plus-08-2024` | Generation model |
| `COHERE_EMBED_MODEL` | `embed-multilingual-v3.0` | Embedding model |
| `COHERE_RERANK_MODEL` | `rerank-multilingual-v3.0` | Reranking model |
| `CHROMA_PERSIST_DIRECTORY` | `./chroma_db` | ChromaDB data directory |
| `CHROMA_COLLECTION_NAME` | `rag_course` | ChromaDB collection |
| `CHUNK_SIZE` | `512` | Tokens per chunk (64–4096) |
| `CHUNK_OVERLAP` | `64` | Token overlap between consecutive chunks |
| `PARENT_CHUNK_SIZE` | `2048` | Parent chunk size for hierarchical chunking |
| `TOP_K_RETRIEVAL` | `10` | Candidate count before reranking |
| `TOP_K_RERANK` | `4` | Final chunks passed to LLM |

---

## Common Commands

### Setup
```bash
poetry install                   # Install all dependencies
poetry install --with dev        # Include dev tools (ruff, mypy, pytest)
cp .env.example .env             # Then edit .env with your API key
```

### Running the API server
```bash
poetry run uvicorn rag_course.api:app --reload --host 0.0.0.0 --port 8000
```

### Running the CLI
```bash
# Ingest documents from a folder
poetry run python -m rag_course.cli ingest --folder ./data/docs

# Ingest specific files
poetry run python -m rag_course.cli ingest --file ./data/docs/Cont_Pilar_Zaragoza.pdf

# Query (ingest optional first)
poetry run python -m rag_course.cli query "What is the payment amount?"

# Query with inline ingest
poetry run python -m rag_course.cli query "What is the start date?" --file ./data/docs/contract.pdf

# Enable debug logging
poetry run python -m rag_course.cli --debug query "..."
```

### Testing
```bash
poetry run pytest                                    # All tests
poetry run pytest --cov=rag_course --cov-report=term-missing  # With coverage
poetry run pytest -m "not integration"               # Skip integration tests
poetry run pytest -m integration                     # Run integration tests only (needs live API)
RUN_INTEGRATION=1 poetry run pytest                  # Integration tests in CI
```

### Linting & formatting
```bash
poetry run ruff check .          # Lint
poetry run ruff format .         # Format
poetry run mypy src/             # Type check
pre-commit run --all-files       # Run all pre-commit hooks
```

### Container (Podman / Docker)
```bash
# Local dev with podman-compose
podman-compose up --build        # Build and start API
podman-compose down              # Stop

# Or using the scripts
bash infra/build.sh              # Build image locally
bash infra/push_ecr.sh           # Push to AWS ECR
bash infra/deploy.sh             # Deploy to EC2 via SSH
```

---

## API Endpoints

Base URL: `http://localhost:8000`

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check → `{"status": "ok"}` |
| `POST` | `/ingest` | Upload a file (PDF or TXT) for ingestion |
| `POST` | `/query` | Ask a question, get a grounded answer |

### POST /ingest
- **Body**: multipart `file` upload
- **Returns**: `{files_processed, documents_processed, chunks_indexed}`

### POST /query
- **Body**: form field `question` (str)
- **Returns**: `{question, answer, model_used, latency_ms, sources: [file_path, ...]}`

---

## Domain Models

All models are **Pydantic v2**, immutable by default. Use `.model_copy(update={...})` to derive updated instances.

| Model | Key fields |
|---|---|
| `Document` | `id` (UUID), `content` (non-empty), `metadata` (DocumentMetadata) |
| `DocumentMetadata` | `source` (DocumentSource enum), `file_path`, `page_number`, `author`, `created_at` |
| `Chunk` | `id` (UUID), `content`, `metadata` (ChunkMetadata), `embedding` (optional list[float]) |
| `ChunkMetadata` | `document_id`, `chunk_index`, `parent_chunk_id` (hierarchical), `hierarchy_level` |
| `QueryResult` | `query`, `answer`, `source_chunks`, `model_used`, `tokens_used`, `latency_ms` |

---

## Ports (Interfaces)

When adding new adapters, implement these abstract classes from `domain/ports.py`:

| Interface | Method signature |
|---|---|
| `IDocumentParser` | `parse(file_path: Path) -> list[Document]` |
| `IChunker` | `chunk(document: Document) -> list[Chunk]` |
| `IEmbedder` | `embed(chunks: list[Chunk]) -> list[Chunk]` |
| `IVectorStore` | `add(chunks)`, `search(query, top_k) -> list[Chunk]` |
| `IRetriever` | `retrieve(query: str, top_k: int) -> list[Chunk]` |
| `ILanguageModel` | `generate(prompt: str) -> str` |

---

## Exception Hierarchy

All domain errors extend `RagCourseError`. Catch the base class unless you need specific handling.

```
RagCourseError
├── DocumentParseError
├── EmbeddingError
├── VectorStoreError
├── LLMError
└── ChunkingError
```

---

## Chunking Strategies

### RecursiveChunker
- LangChain `RecursiveCharacterTextSplitter`
- Configurable `chunk_size` / `chunk_overlap` from settings
- Sequential chunks; metadata includes `chunk_index` and `chunk_total`

### HierarchicalChunker
- Two-level chunking: large **parent** chunks + small **child** chunks
- Children are indexed in ChromaDB (better recall)
- Parents are stored separately for LLM context (better generation quality)
- Use `chunk_with_parents()` to get both levels
- `parent_chunk_id` on each child links back to its parent

---

## Retrieval Pipeline Detail

### CohereReRankRetriever
1. Vector search in ChromaDB for `top_k_retrieval` (default 10) candidates
2. Cohere `rerank-multilingual-v3.0` scores and orders candidates
3. Returns top `top_k_rerank` (default 4) chunks to the use case

### MultiQueryRetriever
1. Uses `ChatCohere` to generate N query variants from the original question
2. Runs vector search for each variant
3. Deduplicates combined results by chunk ID
4. Passes deduplicated pool through Cohere reranking

---

## Infrastructure & Deployment

### Local containers
- **`Containerfile`**: Two-stage build (Poetry export → slim runtime), non-root user (UID 1001), port 8000
- **`compose.yaml`**: Mounts `./data` read-only, persists ChromaDB to a named volume

### AWS (free tier)
- **ECR**: Container registry
- **EC2 t2.micro**: Runs the API as a systemd service
- **SSM Parameter Store**: Stores `COHERE_API_KEY` as a SecureString (no `.env` in production)
- **IAM Role**: Attached to EC2, grants ECR pull + SSM read
- **Security Group**: Opens port 22 (SSH) and 8000 (API)

Provisioning is fully scripted in `infra/create_infrastructure.sh`. First-boot setup (Docker install, SSM key fetch, ECR pull, systemd registration) runs via `infra/ec2_userdata.sh`.

Deployment workflow:
1. `infra/build.sh` — build image
2. `infra/push_ecr.sh` — push to ECR
3. `infra/deploy.sh` — SSH to EC2, pull, restart service

---

## Testing Conventions

- Test directory mirrors source: `tests/domain/`, `tests/infrastructure/`, `tests/application/`
- Unit tests mock all external calls (Cohere API, ChromaDB)
- Integration tests marked `@pytest.mark.integration` — skipped by default; set `RUN_INTEGRATION=1` to enable
- Slow tests marked `@pytest.mark.slow`
- `conftest.py` fixtures: `sample_document`, `sample_chunk`, `doc_metadata`, `sample_query_result`
- Dummy `COHERE_API_KEY` is set in conftest to avoid real credential requirements for unit tests
- Coverage target: 80% (`--cov-fail-under=80`); excludes adapter code (integration-tested), CLI, evaluation

---

## Code Quality

- **Ruff**: line length 88, rules E, F, I (isort), UP, B (bugbear), SIM
- **MyPy**: strict mode; external SDKs (Cohere, ChromaDB, LangChain) use `# type: ignore` where stubs are absent
- **Pre-commit hooks**: trailing whitespace, YAML/TOML validation, ruff format + lint
- Type hints required throughout domain and application layers

---

## Adding a New Adapter

1. Create a file under the appropriate `infrastructure/` subdirectory
2. Implement the relevant port interface from `domain/ports.py`
3. Wire it into `api.py`'s lifespan or the CLI's dependency setup
4. Add unit tests under `tests/infrastructure/`
5. Integration tests go under `tests/integration/` with `@pytest.mark.integration`

Never import concrete adapter classes from inside domain or application code.

---

## Sample Data

`data/docs/Cont_Pilar_Zaragoza.pdf` — A Spanish-language contract document used as the primary test fixture for manual and integration testing.
