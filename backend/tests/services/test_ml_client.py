import pytest
from httpx import Response
from unittest.mock import AsyncMock, patch
from app.services.ml_client import MLClient

@pytest.fixture
def ml_client():
    client = MLClient()
    client._client = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_get_status_disabled(ml_client):
    ml_client._enabled = False
    status = await ml_client.get_status()
    assert status["available"] is False
    assert status["reason"] == "ML service disabled"

@pytest.mark.asyncio
async def test_get_status_success(ml_client):
    ml_client._enabled = True
    ml_client._client.get.return_value = Response(200, json={"train_step": 100})

    status = await ml_client.get_status()
    assert status["available"] is True
    assert status["train_step"] == 100

@pytest.mark.asyncio
async def test_get_status_failure(ml_client):
    ml_client._enabled = True
    ml_client._client.get.return_value = Response(500, text="Internal Server Error")

    status = await ml_client.get_status()
    assert status["available"] is False
    assert "error" in status

@pytest.mark.asyncio
async def test_toggle(ml_client):
    ml_client._enabled = False
    await ml_client.toggle(True)
    assert ml_client._enabled is True

    await ml_client.toggle(False)
    assert ml_client._enabled is False

@pytest.mark.asyncio
async def test_recommend_success(ml_client):
    ml_client._enabled = True
    ml_client._client.post.return_value = Response(200, json={"recommendations": [{"id": 1}]})

    recs = await ml_client.recommend({"test": "state"})
    assert len(recs) == 1
    assert recs[0]["id"] == 1

@pytest.mark.asyncio
async def test_recommend_disabled(ml_client):
    ml_client._enabled = False
    recs = await ml_client.recommend({"test": "state"})
    assert recs == []

@pytest.mark.asyncio
async def test_recommend_failure(ml_client):
    ml_client._enabled = True
    ml_client._client.post.return_value = Response(500)

    recs = await ml_client.recommend({"test": "state"})
    assert recs == []
