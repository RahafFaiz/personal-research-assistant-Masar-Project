"""Load PDF / Markdown / text files into Documents."""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


def _relative_source(path: Path) -> str:
    return path.resolve().relative_to(settings.knowledge_dir.resolve()).as_posix()


def _load_pdf(path: Path, source: str) -> list[Document]:
    from pypdf import PdfReader

    docs = []
    for i, page in enumerate(PdfReader(str(path)).pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            docs.append(Document(page_content=text, metadata={"source": source, "page": i}))
    return docs


def _load_text(path: Path, source: str) -> list[Document]:
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    return [Document(page_content=text, metadata={"source": source})] if text else []


def load_file(path: Path) -> list[Document]:
    path = Path(path)
    source = _relative_source(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(path, source)
    if suffix in (".md", ".txt"):
        return _load_text(path, source)
    logger.warning("Unsupported file skipped: %s", source)
    return []
