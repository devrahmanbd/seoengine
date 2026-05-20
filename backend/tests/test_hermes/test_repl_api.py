import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.api.v1.repl import router, _hermes


@pytest.fixture(autouse=True)
def clear_sessions():
    _hermes.sessions.clear()
    yield


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(router)
    return application


class TestReplApi:
    @pytest.mark.asyncio
    async def test_router_prefix(self):
        assert router.prefix == "/api/v1/repl"

    @pytest.mark.asyncio
    async def test_create_session_returns_session_id(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/repl/session")
            assert resp.status_code == 200
            data = resp.json()
            assert "session_id" in data
            assert isinstance(data["session_id"], str)

    @pytest.mark.asyncio
    async def test_create_session_with_site_id(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/repl/session?site_id=example.com")
            assert resp.status_code == 200
            data = resp.json()
            assert "session_id" in data

    @pytest.mark.asyncio
    async def test_get_session_returns_session(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post("/api/v1/repl/session")
            sid = create.json()["session_id"]
            resp = await client.get(f"/api/v1/repl/session/{sid}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["session_id"] == sid
            assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/repl/session/nonexistent-id")
            assert resp.status_code == 200
            data = resp.json()
            assert "error" in data

    @pytest.mark.asyncio
    async def test_send_command_returns_result(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post("/api/v1/repl/session")
            sid = create.json()["session_id"]
            resp = await client.post(
                f"/api/v1/repl/session/{sid}/command?command=help"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert "output" in data

    @pytest.mark.asyncio
    async def test_send_command_unknown(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post("/api/v1/repl/session")
            sid = create.json()["session_id"]
            resp = await client.post(
                f"/api/v1/repl/session/{sid}/command?command=nonexistent_cmd"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is False

    @pytest.mark.asyncio
    async def test_list_sessions(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/repl/session")
            await client.post("/api/v1/repl/session")
            resp = await client.get("/api/v1/repl/sessions")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) == 2
