"""Retrieval helpers for the Knowledge Agent."""

from __future__ import annotations

from langchain_core.documents import Document

from ..config import settings
from ..schemas import Citation
from . import vector_store


def retrieve(query: str, k: int | None = None) -> list[Document]:
    return vector_store.similarity_search(query, k=k or settings.retriever_top_k)


def to_citation(doc: Document, snippet_chars: int = 200) -> Citation:
    source = doc.metadata.get("source", "unknown")
    section = doc.metadata.get("section")
    page = doc.metadata.get("page")
    label = source
    if section:
        label += f" > {section}"
    if page:
        label += f" (p.{page})"
    snippet = doc.page_content.strip().replace("\n", " ")[:snippet_chars]
    return Citation(source=label, snippet=snippet)
