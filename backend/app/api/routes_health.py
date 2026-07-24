"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.services import ollama_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, object]:
    try:
        await ollama_client.list_models()
        ollama_reachable = True
    except Exception:
        ollama_reachable = False

    return {
        "status": "ok",
        "version": __version__,
        "ollama_reachable": ollama_reachable,
    }