# src/rag_course/infrastructure/parsers/pdf_parser.py
"""
Parseo de PDFs con pdfminer.six.
Extrae texto por página manteniendo la estructura.
"""

from collections.abc import Iterator
from io import StringIO
from pathlib import Path

from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

from rag_course.domain.models import Document, DocumentMetadata, DocumentSource
from rag_course.domain.ports import IDocumentParser


class PdfParser(IDocumentParser):
    """
    Parsea archivos PDF devolviendo un Document por página.
    Preservar la granularidad de página en metadata permite
    citar la fuente exacta al usuario.
    """

    def parse(self, file_path: str) -> list[Document]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo: {file_path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Se esperaba un .pdf, se recibió: {path.suffix}")

        documents: list[Document] = []
        total_pages = self._count_pages(path)

        for page_num, page_text in enumerate(self._extract_pages(path), start=1):
            if not page_text.strip():
                continue  # Saltar páginas vacías o imágenes sin texto

            documents.append(
                Document(
                    content=page_text,
                    metadata=DocumentMetadata(
                        source=DocumentSource.PDF,
                        file_path=str(path.absolute()),
                        page_number=page_num,
                        total_pages=total_pages,
                    ),
                )
            )

        return documents

    def _extract_pages(self, path: Path) -> Iterator[str]:
        """Generador que yield el texto de cada página."""
        with open(path, "rb") as f:
            for page_index, _ in enumerate(PDFPage.get_pages(f)):
                output = StringIO()
                with open(path, "rb") as pdf:
                    extract_text_to_fp(
                        pdf,
                        output,
                        laparams=LAParams(),
                        page_numbers={page_index},
                        output_type="text",
                        codec="utf-8",
                    )
                yield output.getvalue()

    def _count_pages(self, path: Path) -> int:
        with open(path, "rb") as f:
            return sum(1 for _ in PDFPage.get_pages(f))
