"""Workspace Agent — file operations via the Filesystem MCP (sandboxed).

Provides the async MCP primitives; the overwrite confirmation itself lives in
the graph node, which needs LangGraph's interrupt.
"""

from __future__ import annotations

from ..mcp_clients import get_filesystem_tools, tools_by_name
from ..schemas import AgentResult, ResponseStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


async def _tools() -> dict:
    return tools_by_name(await get_filesystem_tools())


async def file_exists(path: str) -> bool:
    tool = (await _tools()).get("get_file_info")
    if tool is None:
        return False
    try:
        result = str(await tool.ainvoke({"path": path})).lower()
        return "not found" not in result and "no such" not in result
    except Exception:
        return False


async def save(path: str, content: str) -> AgentResult:
    tool = (await _tools()).get("write_file")
    if tool is None:
        return AgentResult(status=ResponseStatus.ERROR, error="write_file tool unavailable")
    try:
        await tool.ainvoke({"path": path, "content": content})
    except Exception as e:
        logger.error("Workspace save failed: %s", e)
        return AgentResult(status=ResponseStatus.ERROR, error=str(e))

    logger.info("Report saved to %s", path)
    return AgentResult(content=f"Report saved to {path}")
