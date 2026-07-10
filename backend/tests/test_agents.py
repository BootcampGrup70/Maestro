"""Smoke tests for the agent CRUD endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_agent(client: TestClient, name: str = "Planner") -> dict:
    response = client.post(
        "/api/agents",
        json={
            "name": name,
            "model": "llama3",
            "system_prompt": "You are helpful.",
            "settings": {"temperature": 0.7},
            "canvas_x": 10.0,
            "canvas_y": 20.0,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_get_agent(client: TestClient) -> None:
    created = _create_agent(client)
    assert created["id"]
    assert created["name"] == "Planner"
    assert created["status"] == "idle"
    assert created["settings"] == {"temperature": 0.7}

    fetched = client.get(f"/api/agents/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


def test_list_includes_created_agent(client: TestClient) -> None:
    created = _create_agent(client, name="Researcher")
    listing = client.get("/api/agents")
    assert listing.status_code == 200
    ids = [agent["id"] for agent in listing.json()]
    assert created["id"] in ids


def test_update_position(client: TestClient) -> None:
    created = _create_agent(client)
    response = client.patch(
        f"/api/agents/{created['id']}/position",
        json={"canvas_x": 99.5, "canvas_y": -5.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["canvas_x"] == 99.5
    assert body["canvas_y"] == -5.0


def test_delete_agent(client: TestClient) -> None:
    created = _create_agent(client)
    assert client.delete(f"/api/agents/{created['id']}").status_code == 204
    assert client.get(f"/api/agents/{created['id']}").status_code == 404


def test_get_missing_agent_returns_404(client: TestClient) -> None:
    assert client.get("/api/agents/does-not-exist").status_code == 404
