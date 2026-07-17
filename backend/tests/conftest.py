"""Test fixtures.

We point the app at a throwaway temp-file SQLite DB *before* importing it, so the
module-level engine (created at import time from settings) uses the test database rather
than the real ``maestro.db``.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

_TMP_DIR = Path(tempfile.mkdtemp(prefix="maestro-test-"))
os.environ["MAESTRO_DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DIR / 'test.db'}"
os.environ["MAESTRO_WORKSPACE_DIR"] = str(_TMP_DIR / "workspace")
os.environ["MAESTRO_AUTO_CREATE_TABLES"] = "1"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient that runs the app lifespan (creates tables on the temp DB)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _mock_ollama_models(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must not depend on a live Ollama instance or whatever models happen to be
    pulled on the developer's machine. Every test gets a fixed, predictable model list.
    """

    async def _fake_list_models() -> list[str]:
        return ["llama3", "qwen3:4b", "qwen3:8b"]

    monkeypatch.setattr("app.services.ollama_client.list_models", _fake_list_models)