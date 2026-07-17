"""HuggingFace e5 embeddings for the knowledge base.

The e5 family needs task prefixes ("query: " / "passage: ") to reach its rated
quality; this wrapper applies them so the rest of the pipeline uses the plain
LangChain Embeddings interface. The model is multilingual (Arabic + English).
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings

from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class E5Embeddings(Embeddings):
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.info("Loading embedding model: %s", self.model_name)
        self._backend = HuggingFaceEmbeddings(
            model_name=self.model_name,
            encode_kwargs={"normalize_embeddings": True},
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._backend.embed_documents([f"passage: {t}" for t in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._backend.embed_query(f"query: {text}")


_embeddings: E5Embeddings | None = None


def get_embeddings() -> E5Embeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = E5Embeddings()
    return _embeddings
