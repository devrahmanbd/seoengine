import pytest
from unittest.mock import AsyncMock

from app.services.hermes import HermesAgent, CommandResult, SessionState


class TestCommandResult:
    def test_creation_with_defaults(self):
        r = CommandResult(success=True, output="done")
        assert r.success is True
        assert r.output == "done"
        assert r.data is None
        assert r.reasoning is None
        assert r.duration_ms == 0

    def test_with_all_fields(self):
        r = CommandResult(
            success=False,
            output="error",
            data={"key": "val"},
            reasoning=["step1"],
            duration_ms=100,
        )
        assert not r.success
        assert r.data == {"key": "val"}
        assert r.reasoning == ["step1"]
        assert r.duration_ms == 100


class TestSessionState:
    def test_creation(self):
        s = SessionState(session_id="s1")
        assert s.session_id == "s1"
        assert s.site_id is None
        assert s.memory == {}
        assert s.command_history == []

    def test_with_site_id(self):
        s = SessionState(session_id="s1", site_id="site1")
        assert s.site_id == "site1"


class TestHermesAgent:
    @pytest.fixture
    def agent(self):
        return HermesAgent()

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
    async def test_handle_message_unknown_session(self, agent):
        result = await agent.handle_message("nonexistent", "test")
        assert not result.success
        assert "not found" in result.output

    @pytest.mark.asyncio
    async def test_handle_message_unknown_command(self, agent):
        sid = await agent.create_session()
        result = await agent.handle_message(sid, "nonexistent_command")
        assert not result.success
        assert "Unknown command" in result.output

    @pytest.mark.asyncio
    async def test_register_and_execute_command(self, agent):
        async def handler(input_data: dict) -> str:
            return f"hello {input_data['args'][0] if input_data['args'] else 'world'}"
        agent.register_command("greet", handler)
        sid = await agent.create_session()
        result = await agent.handle_message(sid, "greet testuser")
        assert result.success
        assert result.output == "hello testuser"

    @pytest.mark.asyncio
    async def test_execute_command_with_kwargs(self, agent):
        async def handler(input_data: dict) -> str:
            return f"name={input_data['kwargs'].get('name', 'none')}"
        agent.register_command("show", handler)
        sid = await agent.create_session()
        result = await agent.handle_message(sid, "show --name alice")
        assert result.success
        assert result.output == "name=alice"

    @pytest.mark.asyncio
    async def test_command_history_is_recorded(self, agent):
        async def handler(input_data: dict) -> str:
            return "ok"
        agent.register_command("ping", handler)
        sid = await agent.create_session()
        await agent.handle_message(sid, "ping")
        session = agent.get_session(sid)
        assert len(session.command_history) == 1
        assert session.command_history[0]["command"] == "ping"
        assert session.command_history[0]["success"] is True

    @pytest.mark.asyncio
    async def test_session_last_active_updated(self, agent):
        sid = await agent.create_session()
        session_before = agent.get_session(sid)
        ts_before = session_before.last_active
        async def handler(input_data: dict) -> str:
            return "ok"
        agent.register_command("touch", handler)
        await agent.handle_message(sid, "touch")
        session_after = agent.get_session(sid)
        assert session_after.last_active >= ts_before

    @pytest.mark.asyncio
    async def test_list_sessions(self, agent):
        assert agent.list_sessions() == []
        await agent.create_session(session_id="s1")
        await agent.create_session(session_id="s2")
        assert len(agent.list_sessions()) == 2

    @pytest.mark.asyncio
    async def test_get_session_returns_none_for_missing(self, agent):
        assert agent.get_session("nonexistent") is None

    @pytest.mark.asyncio
    async def test_close_session_removes_it(self, agent):
        sid = await agent.create_session()
        assert agent.get_session(sid) is not None
        await agent.close_session(sid)
        assert agent.get_session(sid) is None

    @pytest.mark.asyncio
    async def test_sync_handler_works(self, agent):
        def sync_handler(input_data: dict) -> str:
            return "sync result"
        agent.register_command("sync_cmd", sync_handler)
        sid = await agent.create_session()
        result = await agent.handle_message(sid, "sync_cmd")
        assert result.success
        assert result.output == "sync result"

    @pytest.mark.asyncio
    async def test_command_result_from_handler(self, agent):
        async def handler(input_data: dict) -> CommandResult:
            return CommandResult(success=True, output="from result", data={"x": 1})
        agent.register_command("result_cmd", handler)
        sid = await agent.create_session()
        result = await agent.handle_message(sid, "result_cmd")
        assert result.success
        assert result.output == "from result"
        assert result.data == {"x": 1}

    @pytest.mark.asyncio
    async def test_handler_exception_caught(self, agent):
        async def failing_handler(input_data: dict) -> str:
            raise RuntimeError("something broke")
        agent.register_command("fail", failing_handler)
        sid = await agent.create_session()
        result = await agent.handle_message(sid, "fail")
        assert not result.success
        assert "something broke" in result.output

    @pytest.mark.asyncio
    async def test_parse_command_simple(self, agent):
        cmd, args, kwargs = await agent._parse_command("deploy --env prod --verbose")
        assert cmd == "deploy"
        assert args == []
        assert kwargs == {"env": "prod", "verbose": "true"}

    @pytest.mark.asyncio
    async def test_parse_command_with_positional_args(self, agent):
        cmd, args, kwargs = await agent._parse_command("analyze site1 site2 --depth 5")
        assert cmd == "analyze"
        assert args == ["site1", "site2"]
        assert kwargs == {"depth": "5"}

    @pytest.mark.asyncio
    async def test_parse_command_empty(self, agent):
        cmd, args, kwargs = await agent._parse_command("")
        assert cmd == ""
        assert args == []
        assert kwargs == {}

    @pytest.mark.asyncio
    async def test_parse_command_flag_without_value(self, agent):
        cmd, args, kwargs = await agent._parse_command("cmd --flag")
        assert cmd == "cmd"
        assert kwargs == {"flag": "true"}

    @pytest.mark.asyncio
    async def test_session_state_has_command_history(self, agent):
        async def handler(input_data: dict) -> str:
            return "ok"
        agent.register_command("hist", handler)
        sid = await agent.create_session()
        await agent.handle_message(sid, "hist")
        await agent.handle_message(sid, "hist")
        session = agent.get_session(sid)
        assert len(session.command_history) == 2
        for entry in session.command_history:
            assert "timestamp" in entry
            assert "command" in entry
