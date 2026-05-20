import asyncio
import json
import logging
import time
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.auth import decode_access_token
from app.services.hermes import HermesAgent, CommandResult
from app.services.hermes.commands import register_all
from app.services.semantic import SemanticDB, LoRASemanticAdapter

logger = logging.getLogger("hermes.api")

router = APIRouter(prefix="/api/v1/repl", tags=["repl"])

_security = HTTPBearer(auto_error=False)

_hermes: HermesAgent | None = None
_semantic_db: SemanticDB | None = None
_lora_adapter: LoRASemanticAdapter | None = None
_startup_time = time.monotonic()


def _ensure_initialized():
    global _semantic_db, _lora_adapter, _hermes
    if _hermes is None:
        _semantic_db = SemanticDB()
        _lora_adapter = LoRASemanticAdapter(_semantic_db)
        _hermes = HermesAgent(semantic_adapter=_lora_adapter)
        register_all(_hermes)


def _verify_token(auth: HTTPAuthorizationCredentials | None = Depends(_security)) -> str | None:
    if auth is None:
        return None
    try:
        payload = decode_access_token(auth.credentials)
        return payload.get("sub", "admin")
    except Exception:
        return None


async def startup_repl() -> None:
    _ensure_initialized()
    if _hermes:
        _hermes.start_sweeper()


async def shutdown_repl() -> None:
    if _hermes:
        await _hermes.persist_all_sessions()
        await _hermes.stop_sweeper()


@router.post("/session")
async def create_session(
    site_id: str | None = None,
    role: str = "user",
    auth: HTTPAuthorizationCredentials | None = Depends(_security),
) -> dict:
    _verify_token(auth)
    _ensure_initialized()
    session_id = await _hermes.create_session(site_id=site_id, role=role)
    return {"session_id": session_id}


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    auth: HTTPAuthorizationCredentials | None = Depends(_security),
) -> dict:
    _verify_token(auth)
    _ensure_initialized()
    session = _hermes.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "session_id": session.session_id,
        "site_id": session.site_id,
        "created_at": session.created_at.isoformat(),
        "last_active": session.last_active.isoformat(),
        "command_count": len(session.command_history),
    }


@router.post("/session/{session_id}/command")
async def send_command(
    session_id: str,
    command: str,
    auth: HTTPAuthorizationCredentials | None = Depends(_security),
) -> CommandResult:
    _verify_token(auth)
    _ensure_initialized()
    return await _hermes.handle_message(session_id, command)


@router.get("/sessions")
async def list_sessions(
    auth: HTTPAuthorizationCredentials | None = Depends(_security),
) -> list[dict]:
    _verify_token(auth)
    _ensure_initialized()
    sessions = _hermes.list_sessions()
    return [
        {
            "session_id": s.session_id,
            "site_id": s.site_id,
            "created_at": s.created_at.isoformat(),
            "last_active": s.last_active.isoformat(),
            "command_count": len(s.command_history),
        }
        for s in sessions
    ]


@router.get("/health")
async def health() -> dict:
    _ensure_initialized()
    uptime_seconds = int(time.monotonic() - _startup_time)
    checks = {}

    if _semantic_db:
        try:
            db_health = await _semantic_db.health()
            checks["semantic_db"] = db_health
        except Exception as e:
            checks["semantic_db"] = {"status": "unhealthy", "error": str(e)}

    if _hermes:
        try:
            agent_health = await _hermes.health()
            checks["hermes_agent"] = agent_health
        except Exception as e:
            checks["hermes_agent"] = {"status": "unhealthy", "error": str(e)}

    if _lora_adapter:
        try:
            adapter_health = await _lora_adapter.health()
            checks["lora_adapter"] = adapter_health
        except Exception as e:
            checks["lora_adapter"] = {"status": "unhealthy", "error": str(e)}

    all_healthy = all(
        c.get("status") == "healthy" for c in checks.values()
    ) if checks else False
    any_unhealthy = any(
        c.get("status") == "unhealthy" for c in checks.values()
    )

    if not checks:
        overall = "degraded"
    elif all_healthy:
        overall = "healthy"
    elif any_unhealthy:
        overall = "unhealthy"
    else:
        overall = "degraded"

    return {
        "status": overall,
        "version": "1.0.0",
        "uptime": uptime_seconds,
        "checks": checks,
    }


@router.get("/health/liveness")
async def liveness() -> dict:
    return {"status": "alive", "uptime": int(time.monotonic() - _startup_time)}


@router.get("/health/readiness")
async def readiness() -> dict:
    _ensure_initialized()
    checks = {}
    if _semantic_db:
        try:
            db_health = await _semantic_db.health()
            checks["semantic_db"] = db_health
        except Exception as e:
            checks["semantic_db"] = {"status": "unhealthy", "error": str(e)}
    if _hermes:
        try:
            agent_health = await _hermes.health()
            checks["hermes_agent"] = agent_health
        except Exception as e:
            checks["hermes_agent"] = {"status": "unhealthy", "error": str(e)}
    all_ready = all(c.get("status") == "healthy" for c in checks.values()) if checks else False
    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
    }


async def _send_disconnect(websocket: WebSocket, reason: str) -> None:
    try:
        await websocket.send_json({"type": "disconnect", "reason": reason})
    except Exception:
        pass


@router.websocket("/session/{session_id}/ws")
async def websocket_terminal(websocket: WebSocket, session_id: str = "anon", token: str = ""):
    if not token:
        await websocket.close(code=4001, reason="missing auth token")
        return
    try:
        from app.core.auth import decode_access_token
        decode_access_token(token)
    except Exception:
        await websocket.close(code=4001, reason="invalid auth token")
        return

    await websocket.accept()
    _ensure_initialized()
    session = _hermes.get_session(session_id)
    is_reconnect = session is not None

    if not session:
        session_id = await _hermes.create_session(session_id=session_id)
        logger.info("ws_connected", extra={"session_id": session_id, "reconnect": False})
    else:
        history = session.command_history
        await websocket.send_json({
            "type": "session_restored",
            "session_id": session_id,
            "history": history,
        })
        logger.info("ws_connected", extra={"session_id": session_id, "reconnect": True, "history_count": len(history)})

    last_active = time.monotonic()
    warning_sent_at: float | None = None
    stop_event = asyncio.Event()
    pending_pong: asyncio.Event | None = None

    async def ping_loop() -> None:
        nonlocal pending_pong
        while not stop_event.is_set():
            try:
                await asyncio.sleep(30)
                if stop_event.is_set():
                    break
                event = asyncio.Event()
                pending_pong = event
                await websocket.send_json({"type": "ping"})
                await asyncio.wait_for(event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                await _send_disconnect(websocket, "ping timeout")
                logger.warning("ws_ping_timeout", extra={"session_id": session_id})
                break
            except asyncio.CancelledError:
                break
            except Exception:
                break
        stop_event.set()

    ping_task = asyncio.create_task(ping_loop())

    try:
        while not stop_event.is_set():
            idle_time = time.monotonic() - last_active

            if idle_time > 240 and warning_sent_at is None:
                try:
                    await websocket.send_json({
                        "type": "warning",
                        "data": "Connection will close due to inactivity",
                        "timeout_seconds": 60,
                    })
                    warning_sent_at = time.monotonic()
                except Exception:
                    break

            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(), timeout=min(60, max(5, 300 - idle_time))
                )
            except asyncio.TimeoutError:
                await _send_disconnect(websocket, "idle timeout")
                logger.info("ws_idle_timeout", extra={"session_id": session_id, "idle_seconds": int(idle_time)})
                break

            last_active = time.monotonic()
            warning_sent_at = None

            try:
                data = json.loads(raw)
                msg_type = data.get("type", "")

                if msg_type == "pong":
                    if pending_pong is not None and not pending_pong.is_set():
                        pending_pong.set()
                        pending_pong = None
                        logger.debug("ws_pong_received", extra={"session_id": session_id})
                    continue

                command = data.get("command", "")
            except (json.JSONDecodeError, TypeError):
                command = raw

            if not command.strip():
                continue

            try:
                await websocket.send_json({"type": "token", "data": f">>> {command}\n"})
                await asyncio.sleep(0.02)

                result = await _hermes.handle_message(session_id, command)

                if result.reasoning:
                    for line in result.reasoning:
                        await websocket.send_json({"type": "reasoning", "data": line})
                        await asyncio.sleep(0.01)

                await websocket.send_json({
                    "type": "result",
                    "data": {
                        "success": result.success,
                        "output": result.output,
                        "data": result.data,
                        "duration_ms": result.duration_ms,
                    },
                })
            except Exception as e:
                logger.exception("ws_message_error", extra={"session_id": session_id, "command": command})
                try:
                    await websocket.send_json({"type": "error", "message": str(e)})
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("ws_disconnected", extra={"session_id": session_id})
    except Exception as e:
        logger.exception("ws_unexpected_error", extra={"session_id": session_id})
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        stop_event.set()
        if not ping_task.done():
            ping_task.cancel()
            try:
                await ping_task
            except (asyncio.CancelledError, Exception):
                pass
