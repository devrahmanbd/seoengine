import asyncio
import json
import pytest
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.hermes import HermesAgent, CommandResult
from app.services.hermes.commands import register_all
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


class TestWebSocketConnection:
    def test_websocket_accepts_connection(self, app):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/repl/session/test-session/ws") as ws:
            ws.send_json({"command": "help"})
            data = ws.receive_json()
            assert data["type"] == "token"
            assert ">>> help" in data["data"]

    def test_websocket_creates_session_if_missing(self, app):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/repl/session/auto-created/ws") as ws:
            ws.send_json({"command": "status"})
            responses = []
            for _ in range(3):
                responses.append(ws.receive_json())
            result = [r for r in responses if r["type"] == "result"]
            assert len(result) >= 1
            assert result[0]["data"]["success"] is True

    def test_websocket_sends_reasoning_and_result(self, app):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/repl/session/reasoning-test/ws") as ws:
            ws.send_json({"command": "help"})
            responses = []
            for _ in range(10):
                responses.append(ws.receive_json())
            types = {r["type"] for r in responses}
            assert "result" in types
            assert "token" in types

    def test_websocket_handles_text_input(self, app):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/repl/session/text-test/ws") as ws:
            ws.send_text("status")
            responses = []
            for _ in range(5):
                responses.append(ws.receive_json())
            result = [r for r in responses if r["type"] == "result"]
            assert len(result) >= 1

    def test_websocket_empty_command_skipped(self, app):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/repl/session/empty-test/ws") as ws:
            ws.send_json({"command": ""})
            ws.send_json({"command": "help"})
            data = ws.receive_json()
            assert data["type"] == "token"

    def test_websocket_error_sends_error_message(self, app):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/repl/session/error-test/ws") as ws:
            ws.send_text("nonexistent_cmd_xyz")
            responses = []
            for _ in range(5):
                responses.append(ws.receive_json())
            result = [r for r in responses if r["type"] == "result"]
            assert len(result) >= 1
            assert result[0]["data"]["success"] is False

    def test_websocket_result_contains_duration(self, app):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/repl/session/duration-test/ws") as ws:
            ws.send_text("help")
            responses = []
            for _ in range(5):
                responses.append(ws.receive_json())
            result = [r for r in responses if r["type"] == "result"]
            assert len(result) >= 1
            assert "duration_ms" in result[0]["data"]
            assert isinstance(result[0]["data"]["duration_ms"], int)

    def test_websocket_invalid_json_handled(self, app):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/repl/session/invalid-json/ws") as ws:
            ws.send_text("not json at all")
            responses = []
            for _ in range(5):
                responses.append(ws.receive_json())
            result = [r for r in responses if r["type"] == "result"]
            assert len(result) >= 1

    def test_websocket_disconnect_does_not_crash(self, app):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/repl/session/disconnect-test/ws") as ws:
            ws.send_text("help")
            ws.receive_json()
        assert True


class TestWebSocketKeepalive:
    def test_multiple_commands_in_one_connection(self, app):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/repl/session/multi-cmd/ws") as ws:
            for cmd in ["help", "status", "help"]:
                ws.send_json({"command": cmd})
                for _ in range(5):
                    try:
                        msg = ws.receive_json(timeout=2)
                        if msg.get("type") == "result":
                            break
                    except Exception:
                        pass
            assert _hermes.get_session("multi-cmd") is not None
            session = _hermes.get_session("multi-cmd")
            assert len(session.command_history) == 3

    def test_websocket_preserves_session_state(self, app):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/repl/session/state-test/ws") as ws:
            ws.send_text("help")
            for _ in range(5):
                try:
                    ws.receive_json(timeout=2)
                except Exception:
                    break
        session = _hermes.get_session("state-test")
        assert session is not None
        assert len(session.command_history) >= 1

    def test_reconnection_restores_session_history(self, app):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/repl/session/reconnect/ws") as ws:
            ws.send_text("help")
            for _ in range(5):
                try:
                    ws.receive_json(timeout=2)
                except Exception:
                    break
        with client.websocket_connect("/api/v1/repl/session/reconnect/ws") as ws:
            ws.send_text("status")
            for _ in range(5):
                try:
                    ws.receive_json(timeout=2)
                except Exception:
                    break
        session = _hermes.get_session("reconnect")
        assert session is not None
        assert len(session.command_history) == 2
        assert session.command_history[0]["command"] == "help"
        assert session.command_history[1]["command"] == "status"
