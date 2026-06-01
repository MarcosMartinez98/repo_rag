from __future__ import annotations

from pathlib import Path

from rag_course.domain.exceptions import DocumentParseError
from rag_course.domain.models import Document, DocumentMetadata, DocumentSource
from rag_course.domain.ports import IDocumentParser


class TextParser(IDocumentParser):
    def parse(self, file_path: str) -> list[Document]:
        path = Path(file_path)
        if not path.exists():
            raise DocumentParseError(f"File not found: {file_path}")
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            raise DocumentParseError(str(exc)) from exc

        return [
            Document(
                content=text,
                metadata=DocumentMetadata(
                    source=DocumentSource.TEXT,
                    file_path=str(path.absolute()),
                ),
            )
        ]
