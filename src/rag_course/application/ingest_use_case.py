# src/rag_course/application/ingest_use_case.py
"""
Caso de uso: ingestar documentos al sistema RAG.
Parse → Chunk → (Embed + Store).
"""

import logging

from rag_course.domain.models import Chunk, Document
from rag_course.domain.ports import IChunker, IDocumentParser, IVectorStore

logger = logging.getLogger(__name__)


class IngestUseCase:
    """
    Orquesta el pipeline de ingesta completo.
    Recibe rutas de ficheros, devuelve estadísticas.
    """

    def __init__(
        self,
        parser: IDocumentParser,
        chunker: IChunker,
        vector_store: IVectorStore,
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._store = vector_store

    def execute(self, file_paths: list[str]) -> dict[str, int]:
        """
        Procesa todos los ficheros dados.
        Devuelve estadísticas: documentos, chunks indexados.
        """
        all_chunks: list[Chunk] = []
        total_docs = 0

        for path in file_paths:
            logger.info("Procesando fichero: %s", path)
            try:
                documents: list[Document] = self._parser.parse(path)
                total_docs += len(documents)

                for doc in documents:
                    chunks = self._chunker.chunk(doc)
                    all_chunks.extend(chunks)
                    logger.debug(
                        "Documento %s → %d chunks generados", doc.id, len(chunks)
                    )

            except Exception as e:
                logger.error("Error procesando %s: %s", path, e)
                raise

        if all_chunks:
            logger.info("Indexando %d chunks en el vector store…", len(all_chunks))
            self._store.add(all_chunks)

        return {
            "documents_processed": total_docs,
            "chunks_indexed": len(all_chunks),
            "files_processed": len(file_paths),
        }
