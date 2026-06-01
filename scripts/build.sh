#!/usr/bin/env bash
# Build the container image locally with Podman.
# Usage:
#   ./scripts/build.sh               # builds rag-course:latest
#   TAG=v1.2.3 ./scripts/build.sh    # builds rag-course:v1.2.3
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-rag-course}"
TAG="${TAG:-latest}"

echo "→ Building ${IMAGE_NAME}:${TAG}..."

podman build \
  --file Containerfile \
  --tag "${IMAGE_NAME}:${TAG}" \
  .

echo "✓ Build complete."
echo "  Run locally: podman run --rm --env-file .env -p 8000:8000 ${IMAGE_NAME}:${TAG}"
