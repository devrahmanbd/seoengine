import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.api.v1.semantic import router
from app.semantic.models import EntityGraph, LoRAContext

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
            assert resp.json()["site_id"] == "s1"

@pytest.mark.asyncio
async def test_get_graph_404(app):
    with patch("app.api.v1.semantic._get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_db.get_graph = AsyncMock(return_value=None)
        mock_get_db.return_value = mock_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/semantic/graph/missing")
            assert resp.status_code == 404

@pytest.mark.asyncio
async def test_post_context_returns_200(app):
    with patch("app.api.v1.semantic._get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_db.get_graph_context = AsyncMock(
            return_value=[{"entity": "SEO", "relevance": 0.95}]
        )
        mock_get_db.return_value = mock_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/semantic/context", json={"site_id": "s1", "query": "SEO"})
            assert resp.status_code == 200
            assert len(resp.json()) == 1

@pytest.mark.asyncio
async def test_get_similar_returns_list(app):
    with patch("app.api.v1.semantic._get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_db.find_similar_sites = AsyncMock(
            return_value=[("s2", 0.8), ("s3", 0.7)]
        )
        mock_get_db.return_value = mock_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/semantic/similar/s1")
            assert resp.status_code == 200
            assert len(resp.json()) == 2
            assert resp.json()[0]["site_id"] == "s2"

@pytest.mark.asyncio
async def test_post_adapt_returns_200(app):
    with patch("app.api.v1.semantic._get_ml") as mock_get_ml:
        mock_ml = AsyncMock()
        mock_ml.enabled = True
        mock_ml.adapt = AsyncMock(return_value={"adapter_id": "a1", "confidence": 0.9})
        mock_get_ml.return_value = mock_ml

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/semantic/adapt", json={"site_id": "s1", "query": "SEO"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["adapter_id"] == "a1"
            assert data["confidence"] == 0.9

@pytest.mark.asyncio
async def test_get_patterns_returns_list(app):
    with patch("app.api.v1.semantic._get_ml") as mock_get_ml:
        mock_ml = AsyncMock()
        mock_ml.enabled = True
        mock_ml.cluster_vectors = AsyncMock(return_value=[["s1", "s2"]])
        mock_ml.find_shared_entities = AsyncMock(return_value=[{"pattern": "p1"}])
        mock_get_ml.return_value = mock_ml

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/semantic/patterns")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_patterns_for_site_returns_200(app):
    with patch("app.api.v1.semantic.get_patterns") as mock_get_patterns:
        mock_get_patterns.return_value = [{"site_id": "s1"}]

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
            json={"site_id": "s1"},
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
         patch("app.api.v1.semantic._get_ml") as mock_get_ml:
        mock_db = AsyncMock()
        mock_db.get_all_site_ids = AsyncMock(return_value=["s1", "s2"])
        mock_db.dimension = 32
        mock_get_db.return_value = mock_db

        mock_ml = AsyncMock()
        mock_ml.enabled = True
        mock_get_ml.return_value = mock_ml

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/semantic/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert "semantic_db" in data
            assert "ml_service" in data
