# ── Stage 1: dependency resolver ──────────────────────────────────────────────
# We use a builder stage just to export a plain requirements.txt from Poetry.
# This way the final image never needs Poetry installed, keeping it smaller.
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir poetry==1.8.3 poetry-plugin-export

WORKDIR /build
COPY pyproject.toml poetry.lock ./

RUN poetry export \
    --without dev \
    --no-interaction \
    --format requirements.txt \
    --output requirements.txt

# ── Stage 2: final runtime image ───────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/MarcosMartinez98/repo_rag"
LABEL org.opencontainers.image.description="RAG Course — API server"

# Security: run as a non-root user.
# UID 1001 avoids conflicts with common system UIDs.
RUN useradd --create-home --uid 1001 --shell /bin/bash appuser

WORKDIR /app

# Install production dependencies from the exported requirements.txt.
# --no-cache-dir keeps the image smaller.
COPY --from=builder /build/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the source package — not tests, scripts, infra, or docs.
COPY src/ ./src/

# ChromaDB stores its data here.
# In production this path is overridden by a mounted volume so data survives restarts.
RUN mkdir -p /app/chroma_db && chown -R appuser:appuser /app

USER appuser

ENV PYTHONPATH=/app/src
ENV CHROMA_PERSIST_DIRECTORY=/app/chroma_db
ENV PORT=8000

EXPOSE 8000

# uvicorn is the ASGI server that runs FastAPI.
# 0.0.0.0 makes it reachable from outside the container.
CMD ["sh", "-c", "uvicorn rag_course.api:app --host 0.0.0.0 --port ${PORT}"]
