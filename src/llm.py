"""LLM factory — OpenRouter (OpenAI-compatible), shared by every agent.

A single model is used for all agents; the `agent` argument is accepted for
compatibility and future per-agent routing.
"""

from __future__ import annotations

from typing import Optional

from .config import settings


def get_llm(temperature: Optional[float] = None, agent: str | None = None):
    from langchain_openai import ChatOpenAI

    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Add your key to .env.")

    return ChatOpenAI(
        model=settings.openrouter_model,
        temperature=settings.llm_temperature if temperature is None else temperature,
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        max_retries=5,   # the free model gets briefly rate-limited upstream; retry through it
        timeout=60,
    )
