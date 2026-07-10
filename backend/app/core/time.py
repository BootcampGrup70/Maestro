"""Time helpers. Timestamps are epoch milliseconds in UTC (see database.md)."""

from __future__ import annotations

import time


def now_ms() -> int:
    """Return the current UTC time as epoch milliseconds."""
    return int(time.time() * 1000)
