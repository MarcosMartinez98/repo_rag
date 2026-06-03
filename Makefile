.PHONY: help install install-dev env \
        api cli-ingest cli-query \
        test test-cov test-unit test-integration \
        lint format typecheck pre-commit \
        build up down \
        infra-create infra-destroy

QUERY ?= What is the payment amount?
PORT ?= 8000

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup"
	@echo "  install          Install core dependencies"
	@echo "  install-dev      Install core + dev dependencies"
	@echo "  env              Copy .env.example to .env (won't overwrite)"
	@echo ""
	@echo "Run"
	@echo "  api              Start FastAPI server (reload enabled)"
	@echo "  cli-ingest       Ingest FILE=<path> (required)"
	@echo "  cli-query        Run QUERY= against the vector store"
	@echo ""
	@echo "Test"
	@echo "  test             Run all unit tests"
	@echo "  test-cov         Run tests with coverage report"
	@echo "  test-unit        Run tests, skip integration"
	@echo "  test-integration Run integration tests only (needs live API)"
	@echo ""
	@echo "Quality"
	@echo "  lint             Ruff lint check"
	@echo "  format           Ruff auto-format"
	@echo "  typecheck        MyPy strict type check"
	@echo "  pre-commit       Run all pre-commit hooks"
	@echo ""
	@echo "Container"
	@echo "  build            Build container image"
	@echo "  up               Start API via podman-compose"
	@echo "  down             Stop containers"
	@echo ""
	@echo "Infrastructure"
	@echo "  infra-create     Provision AWS infrastructure"
	@echo "  infra-destroy    Tear down AWS infrastructure"

# ── Setup ────────────────────────────────────────────────────────────────────

install:
	poetry install

install-dev:
	poetry install --with dev

env:
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example — add your COHERE_API_KEY")

# ── Run ──────────────────────────────────────────────────────────────────────

api:
	poetry run uvicorn rag_course.api:app --reload --host 0.0.0.0 --port $(PORT)

cli-ingest:
	@test -n "$(FILE)" || (echo "Usage: make cli-ingest FILE=<path>"; exit 1)
	poetry run python -m rag_course.cli ingest --file $(FILE)

cli-query:
	poetry run python -m rag_course.cli query "$(QUERY)"

# ── Test ─────────────────────────────────────────────────────────────────────

test:
	poetry run pytest

test-cov:
	poetry run pytest --cov=rag_course --cov-report=term-missing

test-unit:
	poetry run pytest -m "not integration"

test-integration:
	RUN_INTEGRATION=1 poetry run pytest -m integration

# ── Quality ──────────────────────────────────────────────────────────────────

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

typecheck:
	poetry run mypy src/

pre-commit:
	pre-commit run --all-files

# ── Container ────────────────────────────────────────────────────────────────

build:
	bash infra/build.sh

up:
	podman-compose up --build

down:
	podman-compose down

# ── Infrastructure ───────────────────────────────────────────────────────────

infra-create:
	bash infra/create_infrastructure.sh

infra-destroy:
	bash infra/destroy_infrastructure.sh
