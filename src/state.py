"""Shared blackboard state for the supervisor graph."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from .schemas import Citation


class GraphState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    request: str

    research_findings: Annotated[list[str], operator.add]
    citations: Annotated[list[Citation], operator.add]
    draft_report: str
    workspace_path: Optional[str]

    # Every specialist that ran this turn appends {"kind": str, "content": str}
    # here, generically — no per-agent field is hardcoded. The General Assistant
    # joins all of it, so any combination of agents shows up in the final reply.
    results: Annotated[list[dict], operator.add]
    knowledge_done: bool
    saved: bool
    final_reply: str

    next_action: Optional[str]
    payload: dict[str, Any]
    error_count: int

    # None until asked; the user's decision after the overwrite interrupt.
    overwrite_confirmed: Optional[bool]
