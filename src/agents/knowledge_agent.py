"""Knowledge Agent — answers strictly from the user's indexed documents."""

from __future__ import annotations

from ..knowledge import retriever
from ..llm import get_llm
from ..schemas import AgentResult, ResponseStatus
from ..utils.helpers import load_prompt
from ..utils.logger import get_logger

logger = get_logger(__name__)

_REFUSAL = "I don't know based on your notes."


def _build_context(docs) -> str:
    blocks = []
    for i, d in enumerate(docs, start=1):
        src = d.metadata.get("source", "unknown")
        page = d.metadata.get("page")
        label = f"{src} (p.{page})" if page else src
        blocks.append(f"[{i}] Source: {label}\n{d.page_content.strip()}")
    return "\n\n".join(blocks)


def answer_question(query: str) -> AgentResult:
    docs = retriever.retrieve(query)
    if not docs:
        return AgentResult(content=_REFUSAL)

    prompt = load_prompt("knowledge_agent").format(context=_build_context(docs), question=query)
    try:
        answer = (get_llm().invoke(prompt).content or "").strip()
    except Exception as e:
        logger.error("Knowledge Agent LLM call failed: %s", e)
        return AgentResult(status=ResponseStatus.ERROR, error=str(e))

    citations = [] if _REFUSAL.lower() in answer.lower() else [retriever.to_citation(d) for d in docs]
    return AgentResult(content=answer, citations=citations)
