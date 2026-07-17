"""Research Agent — keyless web search (ddgs) with a grounded summary."""

from __future__ import annotations

import time

from ..config import settings
from ..llm import get_llm
from ..schemas import AgentResult, Citation, ResponseStatus
from ..utils.helpers import load_prompt
from ..utils.logger import get_logger

logger = get_logger(__name__)


def _normalize(raw: list[dict]) -> list[dict]:
    return [{
        "title": (r.get("title") or "").strip(),
        "url": r.get("href") or r.get("url") or r.get("link") or "",
        "body": (r.get("body") or r.get("snippet") or "").strip(),
    } for r in raw]


def _web_search(query: str) -> list[dict]:
    from ddgs import DDGS

    last_err: Exception | None = None
    for attempt in range(settings.research_max_retries):
        try:
            with DDGS() as ddg:
                return _normalize(list(ddg.text(query, max_results=settings.research_max_results)))
        except Exception as e:
            last_err = e
            logger.warning("web search attempt %d failed: %s", attempt + 1, e)
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"web search failed: {last_err}")


def _build_context(results: list[dict]) -> str:
    return "\n\n".join(f"[{i}] {r['title']}\nURL: {r['url']}\n{r['body']}"
                       for i, r in enumerate(results, start=1))


def research(topic: str) -> AgentResult:
    try:
        results = _web_search(topic)
    except Exception as e:
        logger.error("Research search failed: %s", e)
        return AgentResult(status=ResponseStatus.ERROR, error=str(e))

    if not results:
        return AgentResult(content="I couldn't find any reliable web results for that topic.")

    prompt = load_prompt("research_agent").format(topic=topic, context=_build_context(results))
    try:
        summary = (get_llm().invoke(prompt).content or "").strip()
    except Exception as e:
        logger.error("Research summary LLM call failed: %s", e)
        return AgentResult(status=ResponseStatus.ERROR, error=str(e))

    citations = [Citation(source=r["url"], title=r["title"], snippet=r["body"][:200])
                 for r in results if r["url"]]
    return AgentResult(content=summary, citations=citations)
