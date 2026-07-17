"""Chroma vector store, persisted under knowledge/vector_store/.

Deterministic per-source chunk IDs plus delete-by-source let the indexer
replace a changed file's vectors without rebuilding the collection.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.documents import Document

from ..config import settings
from ..utils.logger import get_logger
from .embeddings import get_embeddings

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_store():
    from langchain_chroma import Chroma

    settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.collection_name,
        embedding_function=get_embeddings(),
        persist_directory=str(settings.vector_store_dir),
    )


def add_source_chunks(source: str, chunks: list[Document]) -> int:
    if not chunks:
        return 0
    ids = [f"{source}::{c.metadata.get('chunk', i)}" for i, c in enumerate(chunks)]
    get_store().add_documents(documents=chunks, ids=ids)
    logger.info("Indexed %d chunk(s) for '%s'", len(chunks), source)
    return len(chunks)


def delete_source(source: str) -> None:
    get_store().delete(where={"source": source})
    logger.info("Deleted vectors for '%s'", source)


def similarity_search(query: str, k: int | None = None) -> list[Document]:
    return get_store().similarity_search(query, k=k or settings.retriever_top_k)
