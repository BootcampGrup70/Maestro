"""Tool registry / dispatch. v1 has exactly one tool: ``filesystem``.

This indirection exists so a future multi-tool registry (web search, code execution,
custom tools, MCP) can slot in without touching ``run_service``.
"""

from __future__ import annotations

from typing import Any

from app.models.enums import ToolOperation
from app.services.tools import filesystem

# Tool schemas advertised to the model on each chat request.
TOOL_SCHEMAS: list[dict] = [filesystem.FILESYSTEM_TOOL_SCHEMA]


def dispatch(tool_name: str, arguments: dict[str, Any], workspace_dir: str | None = None) -> str:
    """Execute a tool call and return its textual result.

    ``workspace_dir`` overrides the sandbox root for this call (an agent's configured
    ``settings["workspace_dir"]``); ``None`` falls back to the global ``MAESTRO_WORKSPACE_DIR``.

    Raises ``filesystem.FilesystemToolError`` on failure; callers should persist the
    error onto the corresponding ``tool_calls`` row.
    """
    if tool_name != "filesystem":
        raise filesystem.FilesystemToolError(f"Unknown tool: {tool_name!r}")

    operation = arguments.get("operation")
    if operation == ToolOperation.READ.value:
        return filesystem.read_file(arguments["path"], workspace_dir)
    if operation == ToolOperation.WRITE.value:
        return filesystem.write_file(arguments["path"], arguments.get("content", ""), workspace_dir)
    raise filesystem.FilesystemToolError(f"Unknown operation: {operation!r}")
