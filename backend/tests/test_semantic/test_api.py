import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.api.v1.semantic import router
from app.services.semantic.models import EntityGraph, LoRAContext
from app.services.semantic import Pattern


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(router)
    return application


def _mock_graph():
    g = EntityGraph(site_id="s1")
    return g


@pytest.mark.asyncio
async def test_router_has_correct_prefix():
    assert router.prefix == "/api/v1/semantic"


@pytest.mark.asyncio
async def test_get_graph_returns_200(app):
    with patch("app.api.v1.semantic._get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_db.get_graph = AsyncMock(return_value=_mock_graph())
        mock_get_db.return_value = mock_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/semantic/graph/s1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["site_id"] == "s1"


@pytest.mark.asyncio
async def test_get_graph_404(app):
    with patch("app.api.v1.semantic._get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_db.get_graph = AsyncMock(return_value=None)
        mock_get_db.return_value = mock_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/semantic/graph/nonexistent")
            assert resp.status_code == 404


@pytest.mark.asyncio
async def test_post_context_returns_200(app):
    with patch("app.api.v1.semantic._get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_db.get_graph_context = AsyncMock(return_value={
            "site_id": "s1", "query": "SEO",
            "entities": [], "edges": [],
        })
        mock_get_db.return_value = mock_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/semantic/context", json={"site_id": "s1", "query": "SEO"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["site_id"] == "s1"


@pytest.mark.asyncio
async def test_get_similar_returns_list(app):
    with patch("app.api.v1.semantic._get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_db.find_similar_sites = AsyncMock(return_value=[("s2", 0.85), ("s3", 0.72)])
        mock_get_db.return_value = mock_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/semantic/similar/s1")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert data[0]["site_id"] == "s2"


@pytest.mark.asyncio
async def test_post_adapt_returns_200(app):
    mock_ctx = LoRAContext(
        adapter_id="a1", site_id="s1", query="SEO",
        adapted_embedding=[0.1], confidence=0.9,
    )
    with patch("app.api.v1.semantic._get_lora") as mock_get_lora:
        mock_lora = AsyncMock()
        mock_lora.adapt = AsyncMock(return_value=mock_ctx)
        mock_get_lora.return_value = mock_lora

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/semantic/adapt", json={"site_id": "s1", "query": "SEO"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["adapter_id"] == "a1"
            assert data["confidence"] == 0.9


@pytest.mark.asyncio
async def test_get_patterns_returns_list(app):
    with patch("app.api.v1.semantic._get_cross") as mock_get_cross:
        mock_cross = AsyncMock()
        mock_cross.find_patterns = AsyncMock(return_value=[])
        mock_get_cross.return_value = mock_cross

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/semantic/patterns")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_patterns_for_site_returns_200(app):
    with patch("app.api.v1.semantic._get_cross") as mock_get_cross:
        mock_cross = AsyncMock()
        mock_cross.get_insights_for_site = AsyncMock(return_value=[])
        mock_get_cross.return_value = mock_cross

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/semantic/patterns/s1")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)


@pytest.mark.asyncio
async def test_post_context_with_missing_fields_returns_422(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/semantic/context",
            json={},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_adapt_with_missing_fields_returns_422(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/semantic/adapt",
            json={},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_health_returns_200(app):
    with patch("app.api.v1.semantic._get_db") as mock_get_db, \
         patch("app.api.v1.semantic._get_lora") as mock_get_lora, \
         patch("app.api.v1.semantic._get_cross") as mock_get_cross:
        mock_db = AsyncMock()
        mock_db.get_all_site_ids = AsyncMock(return_value=["s1", "s2"])
        mock_db.dimension = 32
        mock_get_db.return_value = mock_db

        mock_lora = AsyncMock()
        mock_lora.rank = 8
        mock_lora.alpha = 0.5
        mock_get_lora.return_value = mock_lora

        mock_cross = AsyncMock()
        mock_cross.min_sites = 2
        mock_get_cross.return_value = mock_cross

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/semantic/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert "semantic_db" in data
            assert "lora_adapter" in data
            assert "cross_site_analyzer" in data
