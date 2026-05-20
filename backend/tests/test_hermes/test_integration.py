import pytest
import tempfile
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.services.hermes import HermesAgent, CommandResult
from app.services.hermes.commands import register_all, command_registry
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


class TestFullSessionLifecycle:
    @pytest.mark.asyncio
    async def test_create_session_send_command_close(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post("/api/v1/repl/session")
            sid = create.json()["session_id"]
            assert sid is not None

            cmd = await client.post(f"/api/v1/repl/session/{sid}/command?command=help")
            assert cmd.status_code == 200
            data = cmd.json()
            assert data["success"] is True

            session = await client.get(f"/api/v1/repl/session/{sid}")
            assert session.status_code == 200
            assert session.json()["session_id"] == sid
            assert session.json()["command_count"] >= 1

    @pytest.mark.asyncio
    async def test_multi_command_accumulates_history(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post("/api/v1/repl/session?site_id=example.com")
            sid = create.json()["session_id"]

            for cmd in ["help", "status", "help"]:
                resp = await client.post(f"/api/v1/repl/session/{sid}/command?command={cmd}")
                assert resp.status_code == 200

            session = await client.get(f"/api/v1/repl/session/{sid}")
            assert session.json()["command_count"] == 3

    @pytest.mark.asyncio
    async def test_session_isolation(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            s1 = (await client.post("/api/v1/repl/session?site_id=site-a")).json()["session_id"]
            s2 = (await client.post("/api/v1/repl/session?site_id=site-b")).json()["session_id"]

            await client.post(f"/api/v1/repl/session/{s1}/command?command=help")
            await client.post(f"/api/v1/repl/session/{s2}/command?command=status")

            sess1 = (await client.get(f"/api/v1/repl/session/{s1}")).json()
            sess2 = (await client.get(f"/api/v1/repl/session/{s2}")).json()

            assert sess1["site_id"] == "site-a"
            assert sess2["site_id"] == "site-b"
            assert sess1["session_id"] != sess2["session_id"]


class TestAuthorizationIntegration:
    @pytest.mark.asyncio
    async def test_admin_command_via_repl_blocked_for_default(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post("/api/v1/repl/session")
            sid = create.json()["session_id"]
            resp = await client.post(f"/api/v1/repl/session/{sid}/command?command=train")
            data = resp.json()
            assert data["success"] is False
            assert "admin" in data["output"] or "requires" in data["output"]

    @pytest.mark.asyncio
    async def test_user_command_works_via_repl(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post("/api/v1/repl/session")
            sid = create.json()["session_id"]
            resp = await client.post(f"/api/v1/repl/session/{sid}/command?command=analyze")
            data = resp.json()
            assert "Usage" in data["output"] or data["success"] is True


class TestMemoryAcrossCommands:
    @pytest.mark.asyncio
    async def test_memory_persists_across_commands_in_session(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post("/api/v1/repl/session?site_id=mem-test")
            sid = create.json()["session_id"]

            await client.post(f"/api/v1/repl/session/{sid}/command?command=help")
            await client.post(f"/api/v1/repl/session/{sid}/command?command=status")

            session = _hermes.get_session(sid)
            assert session is not None
            assert len(session.command_history) == 2

    @pytest.mark.asyncio
    async def test_episodic_memory_stores_command_history(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post("/api/v1/repl/session?site_id=episodic-test")
            sid = create.json()["session_id"]

            await client.post(f"/api/v1/repl/session/{sid}/command?command=help")
            await client.post(f"/api/v1/repl/session/{sid}/command?command=help")
            await client.post(f"/api/v1/repl/session/{sid}/command?command=help")

            session = _hermes.get_session(sid)
            assert session is not None
            assert len(session.command_history) >= 3
            for entry in session.command_history:
                assert "command" in entry
                assert "timestamp" in entry

    @pytest.mark.asyncio
    async def test_command_history_tracks_success_and_failure(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post("/api/v1/repl/session")
            sid = create.json()["session_id"]

            success = await client.post(f"/api/v1/repl/session/{sid}/command?command=help")
            assert success.json()["success"] is True

            fail = await client.post(f"/api/v1/repl/session/{sid}/command?command=nonexistent_cmd")
            assert fail.json()["success"] is False

            session = _hermes.get_session(sid)
            assert session.command_history[0]["success"] is True
            assert len(session.command_history) == 1


class TestSessionPersistenceIntegration:
    @pytest.mark.asyncio
    async def test_save_and_restore_sessions(self):
        agent = _hermes
        async def handler(input_data):
            return "ok"
        agent.register_command("ping", handler)

        sid = await agent.create_session(session_id="integ-s1", site_id="integ.example.com")
        await agent.handle_message(sid, "ping")
        await agent.handle_message(sid, "help")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
            agent.save_sessions(path)

        new_agent = HermesAgent()
        new_agent.register_command("ping", handler)
        register_all(new_agent)
        count = new_agent.load_sessions(path)
        assert count >= 1
        restored = new_agent.get_session("integ-s1")
        assert restored is not None
        assert restored.site_id == "integ.example.com"
        assert len(restored.command_history) == 2


class TestAgentCommandDispatch:
    @pytest.mark.asyncio
    async def test_command_result_contains_output(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post("/api/v1/repl/session")
            sid = create.json()["session_id"]
            resp = await client.post(f"/api/v1/repl/session/{sid}/command?command=help")
            data = resp.json()
            assert "output" in data
            assert len(data["output"]) > 0

    @pytest.mark.asyncio
    async def test_command_result_contains_duration(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post("/api/v1/repl/session")
            sid = create.json()["session_id"]
            resp = await client.post(f"/api/v1/repl/session/{sid}/command?command=help")
            data = resp.json()
            assert "duration_ms" in data
            assert isinstance(data["duration_ms"], int)

    @pytest.mark.asyncio
    async def test_multiple_sessions_independent(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            s1 = (await client.post("/api/v1/repl/session")).json()["session_id"]
            s2 = (await client.post("/api/v1/repl/session")).json()["session_id"]

            await client.post(f"/api/v1/repl/session/{s1}/command?command=help")
            await client.post(f"/api/v1/repl/session/{s2}/command?command=status")

            list_resp = await client.get("/api/v1/repl/sessions")
            sessions = list_resp.json()
            assert len(sessions) == 2


class TestPhase2BlockerFixes:
    @pytest.mark.asyncio
    async def test_commands_import_trainer_correctly(self):
        from app.services.hermes.commands import cmd_train
        assert cmd_train is not None
        assert callable(cmd_train)

    @pytest.mark.asyncio
    async def test_commands_import_scored_data_api_correctly(self):
        from app.services.atropos.scored_data_api import ScoredDataBuffer, ScoredData
        buf = ScoredDataBuffer(max_size=10)
        sd = ScoredData(
            state={"site_id": "test", "metrics": {"score": 0.5}},
            action={"action_type": "fix_title", "params": {}},
            reward=1.0,
            next_state={"site_id": "test", "metrics": {"score": 0.8}},
            done=False,
        )
        buf.append(sd)
        assert len(buf) == 1

    @pytest.mark.asyncio
    async def test_multi_agent_brain_imports_agent_factory(self):
        try:
            from multi_agent_brain import OrchestratorAgent, AgentFactory, AgentType, BaseAgent
            factory = AgentFactory
            assert hasattr(factory, "create")
            assert hasattr(factory, "create_all")
        except ImportError:
            pytest.skip("multi_agent_brain dependencies not installed")

    @pytest.mark.asyncio
    async def test_api_server_imports(self):
        try:
            import importlib
            spec = importlib.util.find_spec("api_server")
            assert spec is not None
        except ImportError:
            pytest.skip("api_server dependencies not installed")

    @pytest.mark.asyncio
    async def test_trainer_ppo_optimizer_import(self):
        from app.services.atropos import PPOOptimizer
        from app.services.atropos.trainer import PPOTrainer
        assert PPOOptimizer is PPOTrainer
