import pytest

from app.services.hermes import HermesAgent, SessionState


@pytest.fixture
def agent():
    a = HermesAgent()
    _register_test_commands(a)
    return a


def _register_test_commands(agent):
    async def handler(input_data):
        return "ok"
    agent.register_command("status", handler, required_role="readonly")
    agent.register_command("help", handler, required_role="readonly")
    agent.register_command("skills", handler, required_role="readonly")
    agent.register_command("analyze", handler, required_role="user")
    agent.register_command("optimize", handler, required_role="user")
    agent.register_command("research", handler, required_role="user")
    agent.register_command("track", handler, required_role="user")
    agent.register_command("train", handler, required_role="admin")
    agent.register_command("decide", handler, required_role="admin")
    agent.register_command("learn", handler, required_role="admin")
    agent.register_command("forget", handler, required_role="admin")


class TestAdminCommands:
    @pytest.mark.asyncio
    async def test_admin_command_blocked_for_user(self, agent):
        sid = await agent.create_session(role="user")
        result = await agent.handle_message(sid, "train")
        assert not result.success
        assert "admin" in result.output or "requires" in result.output

    @pytest.mark.asyncio
    async def test_admin_command_allowed_for_admin(self, agent):
        sid = await agent.create_session(role="admin")
        result = await agent.handle_message(sid, "train")
        assert result.success

    @pytest.mark.asyncio
    async def test_decide_blocked_for_user(self, agent):
        sid = await agent.create_session(role="user")
        result = await agent.handle_message(sid, "decide")
        assert not result.success
        assert "admin" in result.output or "requires" in result.output

    @pytest.mark.asyncio
    async def test_decide_allowed_for_admin(self, agent):
        sid = await agent.create_session(role="admin")
        result = await agent.handle_message(sid, "decide")
        assert result.success

    @pytest.mark.asyncio
    async def test_learn_blocked_for_user(self, agent):
        sid = await agent.create_session(role="user")
        result = await agent.handle_message(sid, "learn test")
        assert not result.success
        assert "admin" in result.output or "requires" in result.output

    @pytest.mark.asyncio
    async def test_forget_blocked_for_user(self, agent):
        sid = await agent.create_session(role="user")
        result = await agent.handle_message(sid, "forget pattern")
        assert not result.success
        assert "admin" in result.output or "requires" in result.output


class TestUserCommands:
    @pytest.mark.asyncio
    async def test_user_command_works_for_user(self, agent):
        sid = await agent.create_session(role="user")
        result = await agent.handle_message(sid, "analyze")
        assert result.success

    @pytest.mark.asyncio
    async def test_user_command_works_for_admin(self, agent):
        sid = await agent.create_session(role="admin")
        result = await agent.handle_message(sid, "analyze")
        assert result.success

    @pytest.mark.asyncio
    async def test_optimize_works_for_user(self, agent):
        sid = await agent.create_session(role="user")
        result = await agent.handle_message(sid, "optimize")
        assert result.success

    @pytest.mark.asyncio
    async def test_research_works_for_user(self, agent):
        sid = await agent.create_session(role="user")
        result = await agent.handle_message(sid, "research")
        assert result.success

    @pytest.mark.asyncio
    async def test_track_works_for_user(self, agent):
        sid = await agent.create_session(role="user")
        result = await agent.handle_message(sid, "track")
        assert result.success


class TestReadonlyCommands:
    @pytest.mark.asyncio
    async def test_status_works_for_user(self, agent):
        sid = await agent.create_session(role="user")
        result = await agent.handle_message(sid, "status")
        assert result.success

    @pytest.mark.asyncio
    async def test_status_works_for_admin(self, agent):
        sid = await agent.create_session(role="admin")
        result = await agent.handle_message(sid, "status")
        assert result.success

    @pytest.mark.asyncio
    async def test_help_works_for_user(self, agent):
        sid = await agent.create_session(role="user")
        result = await agent.handle_message(sid, "help")
        assert result.success

    @pytest.mark.asyncio
    async def test_help_works_for_admin(self, agent):
        sid = await agent.create_session(role="admin")
        result = await agent.handle_message(sid, "help")
        assert result.success

    @pytest.mark.asyncio
    async def test_skills_works_for_user(self, agent):
        sid = await agent.create_session(role="user")
        result = await agent.handle_message(sid, "skills")
        assert result.success

    @pytest.mark.asyncio
    async def test_skills_works_for_admin(self, agent):
        sid = await agent.create_session(role="admin")
        result = await agent.handle_message(sid, "skills")
        assert result.success


class TestAuthorizationErrors:
    @pytest.mark.asyncio
    async def test_unauthorized_returns_proper_message(self, agent):
        sid = await agent.create_session(role="user")
        result = await agent.handle_message(sid, "train")
        assert not result.success
        assert "admin" in result.output or "requires" in result.output
        assert "train" in result.output

    @pytest.mark.asyncio
    async def test_authorize_command_without_session(self, agent):
        authorized, msg = await agent.authorize_command("nonexistent", "status")
        assert not authorized
        assert "Session not found" in msg

    @pytest.mark.asyncio
    async def test_authorize_command_user_on_admin(self, agent):
        sid = await agent.create_session(role="user")
        authorized, msg = await agent.authorize_command(sid, "train")
        assert not authorized
        assert "admin" in msg or "requires" in msg

    @pytest.mark.asyncio
    async def test_authorize_command_admin_on_admin(self, agent):
        sid = await agent.create_session(role="admin")
        authorized, msg = await agent.authorize_command(sid, "train")
        assert authorized
        assert msg == ""

    @pytest.mark.asyncio
    async def test_authorize_command_user_on_user(self, agent):
        sid = await agent.create_session(role="user")
        authorized, msg = await agent.authorize_command(sid, "analyze")
        assert authorized


class TestDefaultRole:
    @pytest.mark.asyncio
    async def test_default_role_is_user(self, agent):
        sid = await agent.create_session()
        assert agent.get_session(sid).role == "user"

    @pytest.mark.asyncio
    async def test_admin_command_blocked_by_default(self, agent):
        sid = await agent.create_session()
        result = await agent.handle_message(sid, "train")
        assert not result.success

    @pytest.mark.asyncio
    async def test_user_command_allowed_by_default(self, agent):
        sid = await agent.create_session()
        result = await agent.handle_message(sid, "analyze")
        assert result.success



