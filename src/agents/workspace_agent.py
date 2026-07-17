"""Workspace Agent — file operations via the Filesystem MCP (sandboxed).

Provides the async MCP primitives; the overwrite confirmation itself lives in
the graph node, which needs LangGraph's interrupt.
"""

from __future__ import annotations

from pathlib import Path

from ..config import settings
from ..mcp_clients import get_filesystem_tools, tools_by_name
from ..schemas import AgentResult, ResponseStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


async def _tools() -> dict:
    return tools_by_name(await get_filesystem_tools())


def _resolve_path(path: str) -> Path:
    """Resolve path to an absolute path within the workspace directory."""
    # Ensure it's treated as relative to workspace even if it has a leading slash
    clean_path = path.lstrip("/\\")
    return (settings.workspace_dir / clean_path).resolve()


async def file_exists(path: str) -> bool:
    tool = (await _tools()).get("get_file_info")
    if tool is None:
        return False
    try:
        abs_path = _resolve_path(path)
        result = str(await tool.ainvoke({"path": str(abs_path)})).lower()
        return "not found" not in result and "no such" not in result
    except Exception:
        return False


async def save(path: str, content: str) -> AgentResult:
    abs_path = _resolve_path(path)
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    # Try MCP tool first; fall back to direct Python write if unavailable (e.g. no Node.js)
    try:
        tool = (await _tools()).get("write_file")
    except Exception:
        tool = None

    if tool is not None:
        try:
            await tool.ainvoke({"path": str(abs_path), "content": content})
            logger.info("Report saved via MCP to %s", path)
            return AgentResult(content=f"Report saved to {path}")
        except Exception as e:
            logger.warning("MCP save failed (%s), falling back to direct write", e)

    # Direct Python fallback
    try:
        abs_path.write_text(content, encoding="utf-8")
        logger.info("Report saved directly to %s", abs_path)
        return AgentResult(content=f"Report saved to {path}")
    except Exception as e:
        logger.error("Direct write failed: %s", e)
        return AgentResult(status=ResponseStatus.ERROR, error=str(e))
