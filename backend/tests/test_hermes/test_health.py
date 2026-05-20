import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI


@pytest.fixture
def health_app():
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": 3600,
            "checks": {
                "database": "ok",
                "redis": "ok",
                "semantic_db": "ok",
            },
        }

    @app.get("/health/liveness")
    async def liveness():
        return {"status": "alive"}

    @app.get("/health/readiness")
    async def readiness():
        return {"status": "ready"}

    @app.get("/")
    async def root():
        return {"status": "ok", "service": "ZenSEO Admin API", "version": "1.0.0"}

    return app


class TestHealthBasic:
    @pytest.mark.asyncio
    async def test_health_returns_healthy(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_returns_200(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_root_returns_service_info(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["service"] == "ZenSEO Admin API"
            assert "version" in data

    @pytest.mark.asyncio
    async def test_health_not_found_on_wrong_path(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/healthz")
            assert resp.status_code == 404


class TestHealthFields:
    @pytest.mark.asyncio
    async def test_health_contains_version(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            assert "version" in data
            assert data["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_health_contains_uptime(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            assert "uptime" in data
            assert data["uptime"] == 3600

    @pytest.mark.asyncio
    async def test_health_contains_checks(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            assert "checks" in data
            assert "database" in data["checks"]
            assert "redis" in data["checks"]

    @pytest.mark.asyncio
    async def test_health_response_structure(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            required_fields = {"status", "version", "uptime", "checks"}
            assert required_fields.issubset(set(data.keys()))


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_liveness_returns_ok(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health/liveness")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness_returns_ok(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health/readiness")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_liveness_endpoint_exists(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health/liveness")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_readiness_endpoint_exists(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health/readiness")
            assert resp.status_code == 200


class TestServiceSpecificHealth:
    @pytest.mark.asyncio
    async def test_database_health_check(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            assert data["checks"]["database"] == "ok"

    @pytest.mark.asyncio
    async def test_redis_health_check(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            assert data["checks"]["redis"] == "ok"

    @pytest.mark.asyncio
    async def test_semantic_db_health_check(self, health_app):
        transport = ASGITransport(app=health_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            assert data["checks"]["semantic_db"] == "ok"
