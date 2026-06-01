import argparse
import json
import logging
import sys
from pathlib import Path

from rag_course.application.ingest_use_case import IngestUseCase
from rag_course.application.query_use_case import QueryUseCase
from rag_course.infrastructure.chunkers.hierarchical_chunker import HierarchicalChunker
from rag_course.infrastructure.llm.cohere_llm import CohereLLM
from rag_course.infrastructure.parsers.pdf_parser import PdfParser
from rag_course.infrastructure.retriever.multi_query_retriever import (
    MultiQueryRetriever,
)
from rag_course.infrastructure.vector_store.chroma_store import ChromaVectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def _build_pipeline() -> tuple[IngestUseCase, QueryUseCase]:
    vector_store = ChromaVectorStore()
    retriever = MultiQueryRetriever(vector_store=vector_store)
    llm = CohereLLM()
    return (
        IngestUseCase(
            parser=PdfParser(), chunker=HierarchicalChunker(), vector_store=vector_store
        ),
        QueryUseCase(retriever=retriever, llm=llm),
    )


def cmd_ingest(args: argparse.Namespace) -> None:
    files: list[str] = []
    if args.folder:
        folder = Path(args.folder)
        files += [str(f) for f in folder.glob("**/*.pdf")] + [
            str(f) for f in folder.glob("**/*.txt")
        ]
    if args.files:
        files += args.files
    if not files:
        logger.error("Indica --folder o al menos un --file")
        sys.exit(1)

    ingest, _ = _build_pipeline()
    stats = ingest.execute(files)
    print(json.dumps(stats, indent=2))


def cmd_query(args: argparse.Namespace) -> None:
    if not args.question:
        logger.error("Indica la pregunta como argumento posicional o con --query")
        sys.exit(1)

    ingest, query_uc = _build_pipeline()

    if args.files:
        logger.info("Indexando ficheros antes de consultar: %s", args.files)
        ingest.execute(args.files)

    result = query_uc.execute(args.question)
    separator = "=" * 60
    print(f"\n{separator}")
    print(f"Pregunta: {result.query}")
    print(separator)
    print(f"\n{result.answer}\n")
    print(separator)
    print(f"Fuentes ({len(result.source_chunks)} chunks) | {result.latency_ms:.0f}ms")
    for chunk in result.source_chunks:
        print(f"  · {chunk.metadata.file_path} (chunk #{chunk.metadata.chunk_index})")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rag-course", description="Sistema RAG de producción"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Activar modo debug (logging detallado)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_p = subparsers.add_parser("ingest", help="Ingestar documentos")
    ingest_p.add_argument("--folder", required=False, help="Carpeta con PDFs/TXTs")
    ingest_p.add_argument(
        "--file", dest="files", action="append", help="Fichero individual (repetible)"
    )

    query_p = subparsers.add_parser("query", help="Hacer una pregunta")
    query_p.add_argument("question", nargs="?", help="La pregunta a responder")
    query_p.add_argument(
        "--query",
        "-q",
        dest="question",
        help="La pregunta a responder (alternativa a argumento posicional)",
    )
    query_p.add_argument(
        "--file",
        dest="files",
        action="append",
        help="Indexar fichero(s) antes de responder (repetible)",
    )

    args = parser.parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Modo debug activado")
    {"ingest": cmd_ingest, "query": cmd_query}[args.command](args)


if __name__ == "__main__":
    # ── Manual debug run ────────────────────────────────────────────────────
    #
    # HOW TO USE THIS SCRIPT
    # ───────────────────────
    # Run directly from the terminal (no CLI arguments needed):
    #
    #     python src/rag_course/cli.py
    #
    # STEP 1 — First time with a new document
    #   Set FILE_TO_INGEST to the path of your PDF or TXT file.
    #   The script will parse it, split it into chunks, embed each chunk
    #   with Cohere, and store the vectors in ChromaDB on disk.
    #   Example:
    #       FILE_TO_INGEST = "./docs/manual.pdf"
    #
    # STEP 2 — Every run after the first
    #   ChromaDB persists the vectors between runs, so you do NOT need to
    #   re-embed the same document again. Set FILE_TO_INGEST = None to skip
    #   the ingest step entirely and go straight to querying.
    #   Example:
    #       FILE_TO_INGEST = None
    #
    # STEP 3 — Set your question
    #   Edit QUERY to whatever you want to ask about the document.
    #   Example:
    #       QUERY = "¿Cuál es la política de devoluciones?"
    #
    # DEBUGGING
    #   Logging is set to DEBUG automatically, so you will see every step
    #   printed to stderr (parse → chunk → embed → retrieve → rerank → LLM).
    #   To step through the code with breakpoints, open this file in your IDE,
    #   place breakpoints wherever you want (e.g. ingest_use_case.py,
    #   multi_query_retriever.py, query_use_case.py), then launch the debugger
    #   targeting this file. The FILE_TO_INGEST / QUERY values below are the
    #   only inputs — no extra configuration is needed.
    #
    FILE_TO_INGEST = r"data\docs\Cont_Pilar_Zaragoza.pdf"  # set to None to skip ingest
    QUERY = "¿El contrato es prorrogable mas de un año?"  # question to ask

    logging.getLogger().setLevel(logging.DEBUG)

    ingest, query_uc = _build_pipeline()

    if FILE_TO_INGEST:
        print("=== INGEST ===")
        stats = ingest.execute([FILE_TO_INGEST])
        print(json.dumps(stats, indent=2))

    print("\n=== QUERY ===")
    result = query_uc.execute(QUERY)
    separator = "=" * 60
    print(f"\n{separator}")
    print(f"Pregunta: {result.query}")
    print(separator)
    print(f"\n{result.answer}\n")
    print(separator)
    print(f"Fuentes ({len(result.source_chunks)} chunks) | {result.latency_ms:.0f}ms")
    for chunk in result.source_chunks:
        print(f"  · {chunk.metadata.file_path} (chunk #{chunk.metadata.chunk_index})")
