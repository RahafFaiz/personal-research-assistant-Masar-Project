"""Orchestrator — routes each turn via structured output (never free text)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ..llm import get_llm
from ..schemas import NextAction, RouteDecision
from ..utils.helpers import load_prompt
from ..utils.logger import get_logger

logger = get_logger(__name__)


class _Route(BaseModel):
    next_action: NextAction
    topic: Optional[str] = Field(default=None, description="search topic for research_agent")
    path: Optional[str] = Field(default=None, description="file path for workspace_agent")
    query: Optional[str] = Field(default=None, description="question for knowledge_agent")


def _yn(v: bool) -> str:
    return "yes" if v else "no"


def _state_summary(state: dict) -> str:
    return (
        f'User request: "{state.get("request", "")}"\n'
        f"Progress:\n"
        f"- knowledge_answered: {_yn(bool(state.get('knowledge_done')))}\n"
        f"- research_done: {_yn(bool(state.get('research_findings')))}\n"
        f"- report_written: {_yn(bool(state.get('draft_report')))}\n"
        f"- report_saved: {_yn(bool(state.get('saved')))}\n"
        f"- final_reply_ready: {_yn(bool(state.get('final_reply')))}\n"
        f"- error_count: {state.get('error_count', 0)}"
    )


def decide(state: dict) -> RouteDecision:
    prompt = load_prompt("orchestrator").format(state_summary=_state_summary(state))
    route: _Route = get_llm(temperature=0).with_structured_output(_Route).invoke(prompt)

    payload = {k: v for k, v in (("topic", route.topic), ("path", route.path), ("query", route.query)) if v}
    return RouteDecision(next_action=route.next_action, payload=payload)
