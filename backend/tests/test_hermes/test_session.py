import json
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from app.services.hermes import HermesAgent, SessionState


@pytest.fixture
def agent():
    return HermesAgent(max_sessions=5)


class TestSessionCreation:
    @pytest.mark.asyncio
    async def test_create_session_returns_id(self, agent):
        sid = await agent.create_session()
        assert sid is not None
        assert isinstance(sid, str)

    @pytest.mark.asyncio
    async def test_create_session_with_site_id(self, agent):
        sid = await agent.create_session(site_id="example.com")
        session = agent.get_session(sid)
        assert session.site_id == "example.com"

    @pytest.mark.asyncio
    async def test_create_session_with_custom_id(self, agent):
        sid = await agent.create_session(session_id="my-session")
        assert sid == "my-session"

    @pytest.mark.asyncio
    async def test_create_session_default_role_is_user(self, agent):
        sid = await agent.create_session()
        session = agent.get_session(sid)
        assert session.role == "user"

    @pytest.mark.asyncio
    async def test_create_session_with_admin_role(self, agent):
        sid = await agent.create_session(role="admin")
        session = agent.get_session(sid)
        assert session.role == "admin"


class TestSessionTTL:
    @pytest.mark.asyncio
    async def test_session_with_ttl_not_expired(self, agent):
        sid = await agent.create_session(ttl=3600)
        assert not agent.get_session(sid).is_expired()

    @pytest.mark.asyncio
    async def test_session_with_ttl_expired(self, agent):
        sid = await agent.create_session(ttl=1)
        session = agent.get_session(sid)
        session.last_active = datetime.now(timezone.utc) - timedelta(seconds=5)
        assert session.is_expired()

    @pytest.mark.asyncio
    async def test_session_without_ttl_never_expires(self, agent):
        sid = await agent.create_session()
        assert not agent.get_session(sid).is_expired()

    @pytest.mark.asyncio
    async def test_expired_session_rejected_on_handle(self, agent):
        sid = await agent.create_session(ttl=1)
        session = agent.get_session(sid)
        session.last_active = datetime.now(timezone.utc) - timedelta(seconds=5)
        result = await agent.handle_message(sid, "status")
        assert not result.success
        assert "expired" in result.output

    @pytest.mark.asyncio
    async def test_touch_updates_last_active(self, agent):
        sid = await agent.create_session(ttl=3600)
        session = agent.get_session(sid)
        old = session.last_active
        session.touch()
        assert session.last_active >= old


class TestSessionSweeper:
    @pytest.mark.asyncio
    async def test_sweep_removes_expired(self, agent):
        await agent.create_session(session_id="keep", ttl=3600)
        await agent.create_session(session_id="remove", ttl=1)
        agent.sessions["remove"].last_active = datetime.now(timezone.utc) - timedelta(seconds=5)
        count = agent.sweep_expired_sessions()
        assert count == 1
        assert agent.get_session("keep") is not None
        assert agent.get_session("remove") is None

    @pytest.mark.asyncio
    async def test_sweep_no_expired(self, agent):
        await agent.create_session(session_id="s1", ttl=3600)
        await agent.create_session(session_id="s2", ttl=3600)
        count = agent.sweep_expired_sessions()
        assert count == 0
        assert len(agent.list_sessions()) == 2

    @pytest.mark.asyncio
    async def test_sweep_all_expired(self, agent):
        await agent.create_session(session_id="s1", ttl=1)
        await agent.create_session(session_id="s2", ttl=1)
        agent.sessions["s1"].last_active = datetime.now(timezone.utc) - timedelta(seconds=5)
        agent.sessions["s2"].last_active = datetime.now(timezone.utc) - timedelta(seconds=5)
        count = agent.sweep_expired_sessions()
        assert count == 2
        assert agent.list_sessions() == []

    @pytest.mark.asyncio
    async def test_sweep_handles_mixed_expiry(self, agent):
        await agent.create_session(session_id="no_ttl")
        await agent.create_session(session_id="expired", ttl=1)
        await agent.create_session(session_id="valid", ttl=3600)
        agent.sessions["expired"].last_active = datetime.now(timezone.utc) - timedelta(seconds=5)
        count = agent.sweep_expired_sessions()
        assert count == 1
        assert agent.get_session("no_ttl") is not None
        assert agent.get_session("valid") is not None
        assert agent.get_session("expired") is None


class TestMaxSessions:
    @pytest.mark.asyncio
    async def test_max_sessions_closes_oldest(self, agent):
        agent.max_sessions = 2
        await agent.create_session(session_id="s1")
        await agent.create_session(session_id="s2")
        await agent.create_session(session_id="s3")
        assert len(agent.list_sessions()) == 2
        assert agent.get_session("s1") is None
        assert agent.get_session("s2") is not None
        assert agent.get_session("s3") is not None

    @pytest.mark.asyncio
    async def test_max_sessions_reuses_existing(self, agent):
        agent.max_sessions = 1
        sid = await agent.create_session(session_id="existing")
        result = await agent.create_session(session_id="existing")
        assert result == "existing"
        assert len(agent.list_sessions()) == 1

    @pytest.mark.asyncio
    async def test_max_sessions_zero_does_not_crash(self, agent):
        agent.max_sessions = 0
        with pytest.raises(ValueError, match="empty"):
            await agent.create_session()

    @pytest.mark.asyncio
    async def test_max_sessions_removes_correct_oldest(self, agent):
        agent.max_sessions = 2
        await agent.create_session(session_id="oldest")
        await agent.create_session(session_id="newer")
        agent.sessions["newer"].touch()
        agent.sessions["oldest"].last_active -= timedelta(hours=1)
        await agent.create_session(session_id="newest")
        assert agent.get_session("oldest") is None
        assert agent.get_session("newer") is not None
        assert agent.get_session("newest") is not None


class TestSessionPersistence:
    @pytest.mark.asyncio
    async def test_save_and_load_sessions(self, agent):
        await agent.create_session(session_id="s1", site_id="example.com", role="admin")
        await agent.create_session(session_id="s2", site_id="test.com")

        async def handler(input_data):
            return "ok"
        agent.register_command("ping", handler)
        await agent.handle_message("s1", "ping")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
            agent.save_sessions(path)

        new_agent = HermesAgent()
        count = new_agent.load_sessions(path)
        assert count == 2
        s1 = new_agent.get_session("s1")
        assert s1 is not None
        assert s1.site_id == "example.com"
        assert s1.role == "admin"
        assert len(s1.command_history) == 1
        s2 = new_agent.get_session("s2")
        assert s2 is not None
        assert s2.site_id == "test.com"

    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self, agent):
        count = agent.load_sessions("/nonexistent/path/sessions.json")
        assert count == 0

    @pytest.mark.asyncio
    async def test_save_empty_sessions(self, agent):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
            agent.save_sessions(path)
        new_agent = HermesAgent()
        count = new_agent.load_sessions(path)
        assert count == 0

    @pytest.mark.asyncio
    async def test_save_load_maintains_command_history(self, agent):
        async def handler(input_data):
            return "ok"
        agent.register_command("ping", handler)
        agent.register_command("status", handler)
        sid = await agent.create_session(session_id="s1")
        await agent.handle_message(sid, "ping")
        await agent.handle_message(sid, "status")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
            agent.save_sessions(path)

        new_agent = HermesAgent()
        new_agent.load_sessions(path)
        restored = new_agent.get_session("s1")
        assert len(restored.command_history) == 2
        assert restored.command_history[0]["command"] == "ping"
        assert restored.command_history[1]["command"] == "status"


class TestSessionRestore:
    @pytest.mark.asyncio
    async def test_create_session_existing_id_restores(self, agent):
        async def handler(input_data):
            return "ok"
        agent.register_command("ping", handler)
        sid = await agent.create_session(session_id="stable", site_id="example.com")
        await agent.handle_message(sid, "ping")
        assert len(agent.get_session("stable").command_history) == 1

        result = await agent.create_session(session_id="stable", site_id="new-site.com")
        assert result == "stable"
        session = agent.get_session("stable")
        assert session.site_id == "new-site.com"
        assert len(session.command_history) == 1

    @pytest.mark.asyncio
    async def test_create_session_existing_id_preserves_history(self, agent):
        async def handler(input_data):
            return "ok"
        agent.register_command("analyze", handler)
        sid = await agent.create_session(session_id="persistent")
        await agent.handle_message(sid, "analyze")
        history_before = len(agent.get_session(sid).command_history)

        await agent.create_session(session_id="persistent")
        assert len(agent.get_session(sid).command_history) == history_before

    @pytest.mark.asyncio
    async def test_create_session_existing_id_updates_role(self, agent):
        await agent.create_session(session_id="s1", role="user")
        await agent.create_session(session_id="s1", role="admin")
        assert agent.get_session("s1").role == "admin"


class TestIdleSweeper:
    @pytest.mark.asyncio
    async def test_sweep_idle_sessions_removes_idle(self, agent):
        agent.idle_timeout = 300
        await agent.create_session(session_id="active")
        await agent.create_session(session_id="idle")
        agent.sessions["idle"].last_active = datetime.now(timezone.utc) - timedelta(seconds=600)
        count = agent.sweep_idle_sessions()
        assert count == 1
        assert agent.get_session("active") is not None
        assert agent.get_session("idle") is None

    @pytest.mark.asyncio
    async def test_sweep_idle_no_timeout_configured(self, agent):
        await agent.create_session(session_id="s1")
        count = agent.sweep_idle_sessions()
        assert count == 0

    @pytest.mark.asyncio
    async def test_sweep_idle_respects_threshold(self, agent):
        agent.idle_timeout = 60
        await agent.create_session(session_id="barely_idle")
        await agent.create_session(session_id="very_idle")
        agent.sessions["barely_idle"].last_active = datetime.now(timezone.utc) - timedelta(seconds=30)
        agent.sessions["very_idle"].last_active = datetime.now(timezone.utc) - timedelta(seconds=120)
        count = agent.sweep_idle_sessions()
        assert count == 1
        assert agent.get_session("barely_idle") is not None
        assert agent.get_session("very_idle") is None
