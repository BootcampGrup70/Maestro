"""UUID helpers. Primary keys are app-generated UUID v4 strings (see database.md)."""

from __future__ import annotations

import uuid


def new_id() -> str:
    """Return a fresh UUID v4 as a string."""
    return str(uuid.uuid4())
