"""Shared filesystem tool - sandboxed read/write within a workspace root.

The workspace root defaults to ``MAESTRO_WORKSPACE_DIR`` but can be overridden per agent
(``agent.settings["workspace_dir"]``, wired in ``run_service``/``registry.dispatch``) so each
agent can be scoped to its own directory. A relative override is resolved as a subdirectory
of the global workspace (still fully sandboxed); an absolute override is used as-is - it's a
human-set value from the agent settings form, not something the model controls.
"""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings


class FilesystemToolError(Exception):
    """Raised for sandbox violations or failed filesystem operations."""


def _workspace_root(root_override: str | None = None) -> Path:
    if root_override:
        override_path = Path(root_override).expanduser()
        root = (
            override_path
            if override_path.is_absolute()
            else get_settings().workspace_dir / override_path
        )
    else:
        root = get_settings().workspace_dir
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_in_workspace(path: str, root_override: str | None = None) -> Path:
    """Resolve ``path`` against the workspace root, rejecting escapes via ``..`` etc."""
    root = _workspace_root(root_override)
    candidate = (root / path).resolve()
    if candidate != root and root not in candidate.parents:
        raise FilesystemToolError(f"Path escapes workspace sandbox: {path!r}")
    return candidate


def read_file(path: str, root_override: str | None = None) -> str:
    """Read and return the contents of a file inside the sandbox."""
    target = resolve_in_workspace(path, root_override)
    try:
        return target.read_text(encoding="utf-8")
    except OSError as exc:
        raise FilesystemToolError(str(exc)) from exc


def write_file(path: str, content: str, root_override: str | None = None) -> str:
    """Write ``content`` to a file inside the sandbox, returning a confirmation string."""
    target = resolve_in_workspace(path, root_override)
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
