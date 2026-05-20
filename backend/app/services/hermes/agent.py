import asyncio
import inspect
import json
import logging
import os
import re
import shlex
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from app.services.semantic.lora import LoRASemanticAdapter
from app.services.hermes.memory import HermesMemory

logger = logging.getLogger(__name__)

ROLE_LEVELS = {"readonly": 0, "user": 1, "admin": 2}


class CommandResult(BaseModel):
    success: bool
    output: str
    data: dict | None = None
    reasoning: list[str] | None = None
    duration_ms: int = 0


class SessionState(BaseModel):
    session_id: str
    site_id: str | None = None
    role: str = "user"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ttl: int | None = None
    memory: dict = Field(default_factory=dict)
    command_history: list[dict] = Field(default_factory=list)

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self.last_active).total_seconds()
        return elapsed > self.ttl

    def touch(self) -> None:
        self.last_active = datetime.now(timezone.utc)


ADMIN_COMMANDS = {"train", "decide", "learn", "forget"}
READONLY_COMMANDS = {"status", "help", "skills"}


class HermesAgent:
    def __init__(
        self,
        semantic_adapter: LoRASemanticAdapter | None = None,
        memory: HermesMemory | None = None,
        max_sessions: int = 10,
        session_ttl: int = 1800,
        persist_dir: str = "/tmp/hermes_sessions/",
        idle_timeout: int | None = None,
    ):
        self.sessions: dict[str, SessionState] = {}
        self._command_registry: dict[str, callable] = {}
        self.memory = memory or HermesMemory()
        self._semantic_adapter = semantic_adapter
        self.max_sessions = max_sessions
        self.session_ttl = session_ttl
        self.idle_timeout = idle_timeout
        self.command_roles: dict[str, str] = {}
        self._persist_dir = Path(persist_dir)
        self._sweeper_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    @property
    def _episodic_memory(self):
        return self.memory.episodic

    def register_command(self, name: str, handler: callable, required_role: str = "user") -> None:
        self._command_registry[name] = handler
        self.command_roles[name] = required_role

    async def create_session(
        self,
        session_id: str | None = None,
        site_id: str | None = None,
        role: str = "user",
        ttl: int | None = None,
    ) -> str:
        # Restore existing session if session_id is provided and exists
        if session_id and session_id in self.sessions:
            existing = self.sessions[session_id]
            if site_id:
                existing.site_id = site_id
            existing.memory["site_id"] = site_id or existing.site_id
            existing.role = role
            return session_id

        sid = session_id or str(uuid4())

        restored = self._restore_session(sid)
        if restored is not None:
            if site_id is not None:
                restored.site_id = site_id
                restored.memory["site_id"] = site_id
            restored.role = role
            self.sessions[sid] = restored
            return sid

        # Enforce max sessions
        if len(self.sessions) >= self.max_sessions:
            oldest_id = min(self.sessions, key=lambda sid: self.sessions[sid].last_active)
            await self.close_session(oldest_id)

        self.sessions[sid] = SessionState(
            session_id=sid,
            site_id=site_id,
            role=role,
            ttl=ttl,
            memory={"site_id": site_id} if site_id else {},
        )
        return sid

    def sweep_expired_sessions(self) -> int:
        """Remove all expired sessions. Returns count of sessions removed."""
        expired = [sid for sid, s in self.sessions.items() if s.is_expired()]
        for sid in expired:
            self.sessions.pop(sid, None)
        return len(expired)

    def sweep_idle_sessions(self) -> int:
        """Remove sessions idle longer than idle_timeout. Returns count removed."""
        if self.idle_timeout is None:
            return 0
        now = datetime.now(timezone.utc)
        idle = [
            sid for sid, s in self.sessions.items()
            if (now - s.last_active).total_seconds() > self.idle_timeout
        ]
        for sid in idle:
            self.sessions.pop(sid, None)
        return len(idle)

    def save_sessions(self, path: str) -> None:
        """Persist all sessions to a JSON file."""
        data = {}
        for sid, session in self.sessions.items():
            data[sid] = {
                "session_id": session.session_id,
                "site_id": session.site_id,
                "role": session.role,
                "created_at": session.created_at.isoformat(),
                "last_active": session.last_active.isoformat(),
                "ttl": session.ttl,
                "memory": session.memory,
                "command_history": session.command_history,
            }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_sessions(self, path: str) -> int:
        """Restore sessions from a JSON file. Returns count loaded."""
        if not os.path.exists(path):
            return 0
        with open(path) as f:
            data = json.load(f)
        count = 0
        for sid, d in data.items():
            d["created_at"] = datetime.fromisoformat(d["created_at"])
            d["last_active"] = datetime.fromisoformat(d["last_active"])
            self.sessions[sid] = SessionState(**d)
            count += 1
        return count

    async def authorize_command(self, session_id: str, command: str) -> tuple[bool, str]:
        """Check if the session's role is authorized for the command."""
        session = self.sessions.get(session_id)
        if not session:
            return False, "Session not found"
        required_role = self.command_roles.get(command, "admin")
        required_level = ROLE_LEVELS.get(required_role, 2)
        session_level = ROLE_LEVELS.get(session.role, 0)
        if session_level < required_level:
            return False, f"Command '{command}' requires {required_role} role"
        return True, ""

    async def handle_message(self, session_id: str, message: str) -> CommandResult:
        start = time.monotonic()
        session = self.sessions.get(session_id)
        if not session:
            return CommandResult(
                success=False,
                output=f"Session '{session_id}' not found",
                duration_ms=0,
            )
        if session.is_expired():
            return CommandResult(
                success=False,
                output="Session has expired. Please create a new session.",
                duration_ms=0,
            )
        session.touch()
        command, args, kwargs = await self._parse_command(message)
        if command not in self._command_registry:
            return CommandResult(
                success=False,
                output=f"Unknown command '{command}'. Available: {', '.join(sorted(self._command_registry.keys()))}",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        authorized, err_msg = await self.authorize_command(session_id, command)
        if not authorized:
            return CommandResult(
                success=False,
                output=err_msg,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        result = await self._react_loop(session, command, args, kwargs)
        session.command_history.append({
            "message": message,
            "command": command,
            "args": args,
            "kwargs": kwargs,
            "success": result.success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        result.duration_ms = int((time.monotonic() - start) * 1000)
        site_id = session.site_id or session_id
        await self.memory.remember_command(session_id, site_id, command, {
            "args": args,
            "kwargs": kwargs,
            "output": result.output,
            "reasoning": result.reasoning,
            "success": result.success,
        })
        return result

    async def _parse_command(self, message: str) -> tuple[str, list[str], dict]:
        message = message.strip()
        if not message:
            return ("", [], {})
        parts = shlex.split(message)
        command = parts[0].lower()
        args: list[str] = []
        kwargs: dict[str, str] = {}
        i = 1
        while i < len(parts):
            part = parts[i]
            if part.startswith("--"):
                key = part[2:]
                if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                    i += 1
                    kwargs[key] = parts[i]
                else:
                    kwargs[key] = "true"
            else:
                args.append(part)
            i += 1
        return (command, args, kwargs)

    async def _react_loop(self, session: SessionState, command: str, args: list[str], kwargs: dict) -> CommandResult:
        reasoning: list[str] = []
        reasoning.append(f"OBSERVE: session={session.session_id}, site={session.site_id}")
        reasoning.append(f"OBSERVE: command={command}, args={args}, kwargs={kwargs}")
        semantic_context = await self._gather_semantic_context(session, command, args)
        if semantic_context:
            reasoning.append(f"OBSERVE: semantic_context=entities:{len(semantic_context.get('entities', []))}, confidence={semantic_context.get('confidence', 0)}")
        site_id = session.site_id or session.session_id
        recent = await self.memory.episodic.recall(site_id, limit=3)
        if recent:
            reasoning.append(f"OBSERVE: recent_history={len(recent)} prior commands")
        reasoning.append(f"REASON: dispatching to handler '{command}'")
        handler = self._command_registry[command]
        try:
            handler_input = {
                "session": session,
                "args": args,
                "kwargs": kwargs,
                "semantic_context": semantic_context,
            }
            if inspect.iscoroutinefunction(handler):
                output = await handler(handler_input)
            else:
                output = handler(handler_input)
            if isinstance(output, CommandResult):
                result = output
            else:
                result = CommandResult(success=True, output=str(output), data={"raw": output})
            result.reasoning = reasoning
            return result
        except Exception as e:
            reasoning.append(f"ACT: error={str(e)}")
            return CommandResult(success=False, output=str(e), reasoning=reasoning)

    async def _gather_semantic_context(self, session: SessionState, command: str, args: list[str]) -> dict | None:
        if not self._semantic_adapter or not session.site_id:
            return None
        query = f"{command} {' '.join(args)}" if args else command
        try:
            ctx = await self._semantic_adapter.adapt(session.site_id, query)
            return ctx.to_dict() if hasattr(ctx, "to_dict") else {
                "adapter_id": ctx.adapter_id,
                "confidence": ctx.confidence,
                "entities": [
                    {"id": e.id, "label": e.label, "type": e.type}
                    for e in getattr(ctx, "top_entities", [])
                ],
            }
        except Exception:
            return None

    def _check_authorization(self, command: str, session: SessionState) -> bool:
        required_role = self.command_roles.get(command, "admin")
        required_level = ROLE_LEVELS.get(required_role, 2)
        session_level = ROLE_LEVELS.get(session.role, 0)
        return session_level >= required_level

    def _persist_session(self, session_id: str) -> None:
        session = self.sessions.get(session_id)
        if session is None:
            return
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        data = session.model_dump()
        data["created_at"] = data["created_at"].isoformat()
        data["last_active"] = data["last_active"].isoformat()
        filepath = self._persist_dir / f"{session_id}.json"
        filepath.write_text(json.dumps(data, indent=2, default=str))

    def _restore_session(self, session_id: str) -> SessionState | None:
        filepath = self._persist_dir / f"{session_id}.json"
        if not filepath.exists():
            return None
        try:
            data = json.loads(filepath.read_text())
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            data["last_active"] = datetime.fromisoformat(data["last_active"])
            session = SessionState(**data)
            filepath.unlink(missing_ok=True)
            return session
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None

    async def _sweep_expired_sessions(self) -> None:
        while not self._stop_event.is_set():
            try:
                now = datetime.now(timezone.utc)
                timeout = self.session_ttl
                expired = [
                    sid
                    for sid, session in self.sessions.items()
                    if (now - session.last_active).total_seconds() > timeout
                ]
                for sid in expired:
                    await self.close_session(sid)
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(60)

    def start_sweeper(self) -> None:
        if self._sweeper_task is not None:
            return
        self._stop_event.clear()
        self._sweeper_task = asyncio.create_task(self._sweep_expired_sessions())

    async def stop_sweeper(self) -> None:
        if self._sweeper_task is None:
            return
        self._stop_event.set()
        self._sweeper_task.cancel()
        try:
            await self._sweeper_task
        except asyncio.CancelledError:
            pass
        self._sweeper_task = None

    async def persist_all_sessions(self) -> None:
        for sid in list(self.sessions.keys()):
            self._persist_session(sid)

    def get_session(self, session_id: str) -> SessionState | None:
        return self.sessions.get(session_id)

    def list_sessions(self) -> list[SessionState]:
        return list(self.sessions.values())

    async def health(self) -> dict:
        memory_status = "healthy"
        try:
            _ = await self.memory.episodic.recall("__health_check__", limit=1)
        except Exception:
            memory_status = "degraded"
        return {
            "status": "healthy",
            "sessions_active": len(self.sessions),
            "commands_available": len(self._command_registry),
            "memory": {
                "status": memory_status,
            },
            "semantic_adapter": self._semantic_adapter is not None,
        }

    async def close_session(self, session_id: str) -> None:
        self._persist_session(session_id)
        self.sessions.pop(session_id, None)
        logger.info("session_closed", extra={"session_id": session_id})
