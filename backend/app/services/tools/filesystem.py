"""Shared filesystem tool - sandboxed read/write within ``WORKSPACE_DIR``.

The path-safety helpers below are complete; wiring these into the model tool-calling
loop (parsing Ollama tool calls, persisting ``tool_calls`` rows, feeding results back to
the model) is the main open task for the team - see ``run_service._handle_tool_calls``.
"""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings


class FilesystemToolError(Exception):
    """Raised for sandbox violations or failed filesystem operations."""


def _workspace_root() -> Path:
    root = get_settings().workspace_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_in_workspace(path: str) -> Path:
    """Resolve ``path`` against the workspace root, rejecting escapes via ``..`` etc."""
    root = _workspace_root()
    candidate = (root / path).resolve()
    if candidate != root and root not in candidate.parents:
        raise FilesystemToolError(f"Path escapes workspace sandbox: {path!r}")
    return candidate


def read_file(path: str) -> str:
    """Read and return the contents of a file inside the sandbox."""
    target = resolve_in_workspace(path)
    try:
        return target.read_text(encoding="utf-8")
    except OSError as exc:
        raise FilesystemToolError(str(exc)) from exc


def write_file(path: str, content: str) -> str:
    """Write ``content`` to a file inside the sandbox, returning a confirmation string."""
    target = resolve_in_workspace(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise FilesystemToolError(str(exc)) from exc
    return f"Wrote {len(content)} bytes to {path}"


# Ollama tool schema for the single shared filesystem tool. Passed to the model so it can
# decide to call read/write. See https://github.com/ollama/ollama/blob/main/docs/api.md
FILESYSTEM_TOOL_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "filesystem",
        "description": "Read from or write to a file in the local workspace sandbox.",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["read", "write"]},
                "path": {"type": "string", "description": "Path relative to the workspace root."},
                "content": {"type": "string", "description": "Content to write (write only)."},
            },
            "required": ["operation", "path"],
        },
    },
}
