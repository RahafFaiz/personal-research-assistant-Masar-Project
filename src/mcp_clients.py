"""Filesystem MCP client, sandboxed to the workspace directory."""

from __future__ import annotations

import json
import platform
import shutil
from typing import Any

from .config import PROJECT_ROOT, settings
from .utils.logger import get_logger

logger = get_logger(__name__)

MCP_CONFIG_PATH = PROJECT_ROOT / "config" / "mcp_servers.json"


def _resolve_command(command: str) -> str:
    resolved = shutil.which(command)
    if resolved:
        return resolved
    # On Windows npx is npx.cmd, which the raw name won't resolve to.
    if platform.system() == "Windows":
        cmd = shutil.which(f"{command}.cmd")
        if cmd:
            return cmd
    return command


def load_server_config() -> dict[str, dict[str, Any]]:
    """Read mcp_servers.json, resolving <WORKSPACE_DIR> to the absolute sandbox path."""
    raw = json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8"))
    settings.workspace_dir.mkdir(parents=True, exist_ok=True)
    workspace_abs = str(settings.workspace_dir.resolve())

    connections: dict[str, dict[str, Any]] = {}
    for name, cfg in raw.get("mcpServers", {}).items():
        if name.startswith("_"):
            continue
        connections[name] = {
            "command": _resolve_command(cfg["command"]),
            "args": [str(a).replace("<WORKSPACE_DIR>", workspace_abs) for a in cfg.get("args", [])],
            "transport": cfg.get("transport", "stdio"),
        }
    return connections


def get_mcp_client():
    from langchain_mcp_adapters.client import MultiServerMCPClient

    return MultiServerMCPClient(load_server_config())


async def get_filesystem_tools() -> list:
    tools = await get_mcp_client().get_tools()
    logger.info("Loaded %d filesystem MCP tool(s)", len(tools))
    return tools


def tools_by_name(tools: list) -> dict[str, Any]:
    return {t.name: t for t in tools}
