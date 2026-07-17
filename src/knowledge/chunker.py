"""Structure-aware chunking.

Chunks are built at meaningful boundaries so each is self-contained:
markdown splits on headings; PDF/text splits on detected section headings
(a general heuristic, not hardcoded names). Each chunk is prefixed with a
"<source> > <section>" breadcrumb and sections over the size cap are split
recursively.
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from ..config import settings

_recursive = RecursiveCharacterTextSplitter(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
    separators=["\n\n", "\n", ". ", " ", ""],
)

_md_header = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
    strip_headers=False,
)


def _is_heading(line: str) -> bool:
    """A short standalone line with no digits or trailing punctuation."""
    s = line.strip()
    if not s or s[0] in "•-*" or any(c.isdigit() for c in s) or s[-1] in ".,:;":
        return False
    return len(s.split()) <= 3


def _emit(source: str, section: str | None, text: str, out: list[Document]) -> None:
    text = text.strip()
    if not text:
        return
    breadcrumb = f"{source} > {section}" if section else source
    pieces = [text] if len(text) <= settings.chunk_size else _recursive.split_text(text)
    for p in pieces:
        content = f"{breadcrumb}\n{p}" if section else p
        out.append(Document(page_content=content, metadata={"source": source, "section": section or ""}))


def _chunk_structured_text(source: str, text: str) -> list[Document]:
    out: list[Document] = []
    section, buffer = None, []
    for line in text.splitlines():
        if _is_heading(line):
            _emit(source, section, "\n".join(buffer), out)
            section, buffer = line.strip(), []
        else:
            buffer.append(line)
    _emit(source, section, "\n".join(buffer), out)
    return out


def _chunk_markdown(source: str, text: str) -> list[Document]:
    out: list[Document] = []
    for d in _md_header.split_text(text):
        section = " > ".join(str(v) for v in d.metadata.values()) or None
        _emit(source, section, d.page_content, out)
    return out


def chunk_documents(docs: list[Document]) -> list[Document]:
    out: list[Document] = []
    counters: dict[str, int] = {}
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page")
        chunks = (
            _chunk_markdown(source, doc.page_content)
            if source.lower().endswith(".md")
            else _chunk_structured_text(source, doc.page_content)
        )
        for c in chunks:
            c.metadata["chunk"] = counters.get(source, 0)
            counters[source] = c.metadata["chunk"] + 1
            if page is not None:
                c.metadata["page"] = page
            out.append(c)
    return out
