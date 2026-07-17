"""Typed contracts shared between agents and the graph."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class NextAction(str, Enum):
    GENERAL_ASSISTANT = "general_assistant"
    KNOWLEDGE_AGENT = "knowledge_agent"
    RESEARCH_AGENT = "research_agent"
    REPORT_WRITER = "report_writer"
    WORKSPACE_AGENT = "workspace_agent"
    FINISH = "FINISH"


class RouteDecision(BaseModel):
    """The Orchestrator's routing output."""

    next_action: NextAction
    payload: dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = None


class Citation(BaseModel):
    source: str                       # file path (knowledge) or URL (research)
    snippet: Optional[str] = None
    title: Optional[str] = None


class AgentResult(BaseModel):
    """Normalized result returned by a specialist agent."""

    status: ResponseStatus = ResponseStatus.SUCCESS
    content: str = ""
    citations: list[Citation] = Field(default_factory=list)
    error: Optional[str] = None
