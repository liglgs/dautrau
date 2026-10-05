import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_route_is_removed_from_mvp(client):
    """Route chat của template đã bị gỡ: mọi lượt phải đi qua /investigations."""
    response = await client.post("/api/v1/chat", json={"message": ""})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_agent_status(client):
    response = await client.get("/api/v1/status")
    assert response.status_code == 200
