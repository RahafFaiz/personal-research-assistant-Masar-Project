"""Supervisor graph: Orchestrator routes each turn; the General Assistant ends.

    START -> orchestrator -> (specialist -> orchestrator)* -> general_assistant -> END

A checkpointer enables the Workspace Agent's overwrite interrupt.
"""

from __future__ import annotations

import re

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .agents import (
    general_assistant,
    knowledge_agent,
    orchestrator,
    report_writer,
    research_agent,
)
from .agents import workspace_agent as workspace
from .config import settings
from .schemas import AgentResult
from .state import GraphState
from .utils.logger import get_logger

logger = get_logger(__name__)


def _specialist_update(kind: str, res: AgentResult) -> dict:
    # Appends generically to `results` — the General Assistant reads this list
    # without knowing which specialists produced it, so any combination of
    # agents (one, several, or all) ends up in the final reply.
    update: dict = {"results": [{"kind": kind, "content": res.content}]} if res.content else {}
    if res.citations:
        update["citations"] = res.citations
    if res.status.value == "error":
        update["error_count"] = 1
    return update


def _orchestrator_node(state: GraphState) -> dict:
    decision = orchestrator.decide(state)
    action = decision.next_action.value
    payload = dict(decision.payload)

    knowledge_done = bool(state.get("knowledge_done"))
    research_done = bool(state.get("research_findings"))
    report_done = bool(state.get("draft_report"))
    saved = bool(state.get("saved"))
    wants_save = bool(state.get("workspace_path") or payload.get("path"))

    # Loop guards: the Orchestrator still directs every turn — these only stop it
    # from re-running a specialist whose work is already done.
    if action == "knowledge_agent" and knowledge_done:
        action = "general_assistant"
    elif action == "research_agent" and research_done:
        action = "report_writer" if (wants_save and not report_done) else "general_assistant"
    elif action == "report_writer" and report_done:
        action = "workspace_agent" if (wants_save and not saved) else "general_assistant"
    elif action == "workspace_agent" and saved:
        action = "general_assistant"

    logger.info("Orchestrator -> %s %s", action, payload or "")
    return {"next_action": action, "payload": payload}


def _knowledge_node(state: GraphState) -> dict:
    query = state.get("payload", {}).get("query") or state.get("request", "")
    res = knowledge_agent.answer_question(query)
    return {**_specialist_update("knowledge", res), "knowledge_done": True}


def _research_node(state: GraphState) -> dict:
    topic = state.get("payload", {}).get("topic") or state.get("request", "")
    res = research_agent.research(topic)
    update = _specialist_update("research", res)
    if res.content:
        update["research_findings"] = [res.content]
    return update


def _report_node(state: GraphState) -> dict:
    topic = state.get("payload", {}).get("topic") or state.get("request", "")
    res = report_writer.write_report(topic, state.get("research_findings", []), state.get("citations", []))
    update = _specialist_update("report", res)
    if res.content:
        update["draft_report"] = res.content
    return update


async def _workspace_node(state: GraphState) -> dict:
    path = state.get("payload", {}).get("path") or state.get("workspace_path")
    if not path:
        return _specialist_update("workspace", AgentResult(content="No target path was provided."))

    exists = await workspace.file_exists(path)
    confirmed = state.get("overwrite_confirmed")
    if exists and confirmed is None:
        confirmed = interrupt({"type": "overwrite_confirm", "path": path})

    if exists and confirmed is False:
        res = AgentResult(content=f"Save cancelled — {path} was not overwritten.")
        return {**_specialist_update("workspace", res), "saved": False, "overwrite_confirmed": False}

    res = await workspace.save(path, state.get("draft_report", ""))
    return {**_specialist_update("workspace", res), "saved": True, "workspace_path": path}


def _general_node(state: GraphState) -> dict:
    # Generic assembly: join every specialist result gathered this run, in the
    # order they ran, regardless of which agents or how many were involved.
    content = "\n\n".join(r["content"] for r in state.get("results", []) if r.get("content")).strip()

    if not content:
        reply = general_assistant.chat(state.get("request", ""))
    else:
        result = AgentResult(content=content, citations=state.get("citations", []))
        reply = general_assistant.phrase(state.get("request", ""), result)

    return {"final_reply": reply, "messages": [AIMessage(content=reply)]}


def _route(state: GraphState):
    action = state.get("next_action")
    return END if action in (None, "FINISH") else action


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("orchestrator", _orchestrator_node)
    g.add_node("knowledge_agent", _knowledge_node)
    g.add_node("research_agent", _research_node)
    g.add_node("report_writer", _report_node)
    g.add_node("workspace_agent", _workspace_node)
    g.add_node("general_assistant", _general_node)

    g.add_edge(START, "orchestrator")
    g.add_conditional_edges("orchestrator", _route, {
        "knowledge_agent": "knowledge_agent",
        "research_agent": "research_agent",
        "report_writer": "report_writer",
        "workspace_agent": "workspace_agent",
        "general_assistant": "general_assistant",
        END: END,
    })
    # Every specialist returns to the Orchestrator, which directs each turn and
    # decides when the task is complete; the General Assistant ends the run.
    for node in ("knowledge_agent", "research_agent", "report_writer", "workspace_agent"):
        g.add_edge(node, "orchestrator")
    g.add_edge("general_assistant", END)

    return g.compile(checkpointer=MemorySaver())


_SAVE_PATH = re.compile(r"([\w./-]+\.md)", re.I)


def _extract_save_path(request: str) -> str | None:
    match = _SAVE_PATH.search(request)
    return match.group(1) if match else None


def initial_state(request: str) -> dict:
    state = {"request": request, "messages": [HumanMessage(content=request)], "error_count": 0}
    path = _extract_save_path(request)
    if path:
        state["workspace_path"] = path
    return state


def run_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": settings.recursion_limit}
