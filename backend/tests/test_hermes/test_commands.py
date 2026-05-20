import pytest
from unittest.mock import AsyncMock, patch

from app.services.hermes import HermesAgent, CommandResult
from app.services.hermes.commands import (
    command_registry,
    register_all,
    cmd_analyze,
    cmd_help,
    cmd_status,
    cmd_semantic,
)


class TestCommandRegistry:
    def test_register_all_registers_expected_commands(self):
        agent = HermesAgent()
        register_all(agent)
        expected = {"analyze", "optimize", "train", "decide", "research", "track", "status", "help"}
        registered = set(agent._command_registry.keys())
        assert expected.issubset(registered)

    def test_command_registry_has_handlers(self):
        assert len(command_registry) >= 10


class TestCmdAnalyze:
    @pytest.mark.asyncio
    async def test_analyze_with_url_and_env_all(self):
        result = await cmd_analyze("session-1", ["https://example.com"], {"env": "all"})
        assert isinstance(result, CommandResult)
        assert result.data is not None
        assert "Audio" not in result.output.replace("example.com", "")
        assert "Audit for example.com" in result.output or "Audit for" in result.output
        assert result.data["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_analyze_no_url_returns_usage(self):
        result = await cmd_analyze("session-1", [], {})
        assert not result.success
        assert "Usage" in result.output


class TestCmdHelp:
    @pytest.mark.asyncio
    async def test_help_with_topic(self):
        result = await cmd_help("session-1", ["analyze"], {})
        assert result.success is True
        assert "analyze" in result.output
        assert "<url>" in result.output

    @pytest.mark.asyncio
    async def test_help_without_topic(self):
        result = await cmd_help("session-1", [], {})
        assert result.success is True
        assert "Available Commands" in result.output

    @pytest.mark.asyncio
    async def test_help_unknown_topic(self):
        result = await cmd_help("session-1", ["nonexistent"], {})
        assert not result.success


class TestCmdStatus:
    @pytest.mark.asyncio
    async def test_status_returns_system_info(self):
        result = await cmd_status("session-1", [], {})
        assert result.success is True
        assert "System Health" in result.output
        assert result.data is not None
        assert "commands" in result.data


class TestCmdSemantic:
    @pytest.mark.asyncio
    async def test_semantic_with_query_no_adapter(self):
        result = await cmd_semantic("session-1", ["SEO", "tools"], {})
        assert result.success is True
        assert "SEO tools" in result.output


class TestRegisterAll:
    @pytest.mark.asyncio
    async def test_register_all_then_dispatch(self):
        agent = HermesAgent()
        register_all(agent)
        sid = await agent.create_session()
        result = await agent.handle_message(sid, "help")
        assert result.success is True
        assert "Available Commands" in result.output

    @pytest.mark.asyncio
    async def test_help_command_registered(self):
        agent = HermesAgent()
        register_all(agent)
        sid = await agent.create_session(site_id="example.com")
        result = await agent.handle_message(sid, "help")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_status_command_via_agent(self):
        agent = HermesAgent()
        register_all(agent)
        sid = await agent.create_session(site_id="example.com")
        result = await agent.handle_message(sid, "status")
        assert result.success is True
        assert "System Health" in result.output
