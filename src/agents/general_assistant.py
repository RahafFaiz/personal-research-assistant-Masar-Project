"""General Assistant — the only voice the user hears.

phrase() turns a specialist result into the final reply (preserving citations
and paths verbatim); chat() answers simple messages directly.
"""

from __future__ import annotations

from ..llm import get_llm
from ..schemas import AgentResult
from ..utils.citations import render_citations
from ..utils.helpers import load_prompt


def chat(user_message: str) -> str:
    prompt = load_prompt("general_assistant_chat").format(message=user_message)
    return (get_llm().invoke(prompt).content or "").strip()


def phrase(user_message: str, specialist: AgentResult) -> str:
    prompt = load_prompt("general_assistant").format(
        message=user_message,
        content=specialist.content,
        sources=render_citations(specialist.citations),
    )
    return (get_llm().invoke(prompt).content or "").strip()


def respond(user_message: str, specialist: AgentResult | None = None) -> str:
    return chat(user_message) if specialist is None else phrase(user_message, specialist)
