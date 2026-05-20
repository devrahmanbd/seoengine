import os
import json
import fnmatch
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Any
from asyncio import get_event_loop, AbstractEventLoop


@dataclass
class MemoryEntry:
    key: str
    content: str | dict
    timestamp: datetime | None = None
    ttl: int | None = None
    tags: list[str] | None = None


def _to_dict(entry: MemoryEntry) -> dict:
    d = asdict(entry)
    ts = d.get("timestamp")
    if ts is None:
        d["timestamp"] = _now().isoformat()
    elif isinstance(ts, datetime):
        d["timestamp"] = ts.isoformat()
    return d


def _from_dict(d: dict) -> MemoryEntry:
    ts = d.get("timestamp")
    if isinstance(ts, str):
        d["timestamp"] = datetime.fromisoformat(ts)
    elif ts is None:
        d["timestamp"] = _now()
    return MemoryEntry(**d)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _aio_write(path: str, data: str, loop: AbstractEventLoop | None = None) -> None:
    loop = loop or get_event_loop()
    await loop.run_in_executor(None, _sync_write, path, data)


def _sync_write(path: str, data: str) -> None:
    with open(path, "w") as f:
        f.write(data)


async def _aio_read(path: str, loop: AbstractEventLoop | None = None) -> str:
    loop = loop or get_event_loop()
    return await loop.run_in_executor(None, _sync_read, path)


def _sync_read(path: str) -> str:
    with open(path) as f:
        return f.read()


async def _aio_readlines(path: str, loop: AbstractEventLoop | None = None) -> list[str]:
    loop = loop or get_event_loop()
    return await loop.run_in_executor(None, _sync_readlines, path)


def _sync_readlines(path: str) -> list[str]:
    with open(path) as f:
        return f.readlines()


async def _aio_append(path: str, line: str, loop: AbstractEventLoop | None = None) -> None:
    loop = loop or get_event_loop()
    await loop.run_in_executor(None, _sync_append, path, line)


def _sync_append(path: str, line: str) -> None:
    with open(path, "a") as f:
        f.write(line)


class WorkingMemory:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def set(self, session_id: str, key: str, value: Any) -> None:
        self._store.setdefault(session_id, {})[key] = value

    def get(self, session_id: str, key: str, default: Any = None) -> Any:
        return self._store.get(session_id, {}).get(key, default)

    def delete(self, session_id: str, key: str) -> None:
        self._store.get(session_id, {}).pop(key, None)

    def clear_session(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def snapshot(self, session_id: str) -> dict[str, Any]:
        return dict(self._store.get(session_id, {}))


class EpisodicMemory:
    def __init__(self, storage_dir: str | None = None) -> None:
        self._storage_dir = storage_dir or os.path.join(os.getcwd(), "data", "episodic")
        os.makedirs(self._storage_dir, exist_ok=True)

    def _site_path(self, site_id: str) -> str:
        sanitized = site_id.replace("/", "_").replace("\\", "_")
        return os.path.join(self._storage_dir, f"{sanitized}.json")

    async def store(self, site_id: str, entry: MemoryEntry) -> None:
        path = self._site_path(site_id)
        entry.timestamp = entry.timestamp or _now()
        line = json.dumps(_to_dict(entry)) + "\n"
        loop = get_event_loop()
        await loop.run_in_executor(None, self._sync_store, path, line)

    def _sync_store(self, path: str, line: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(line)

    async def recall(
        self, site_id: str, query: str | None = None, limit: int = 20
    ) -> list[MemoryEntry]:
        path = self._site_path(site_id)
        if not os.path.exists(path):
            return []
        loop = get_event_loop()
        lines = await loop.run_in_executor(None, _sync_readlines, path)
        results: list[MemoryEntry] = []
        now = _now()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                entry = _from_dict(d)
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
            if entry.ttl is not None and entry.timestamp is not None:
                elapsed = (_now() - entry.timestamp).total_seconds()
                if elapsed > entry.ttl:
                    continue
            if query:
                if not self._matches_query(entry, query):
                    continue
            results.append(entry)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def _matches_query(self, entry: MemoryEntry, query: str) -> bool:
        q = query.lower()
        if q in entry.key.lower():
            return True
        if isinstance(entry.content, str) and q in entry.content.lower():
            return True
        if isinstance(entry.content, dict):
            if q in json.dumps(entry.content).lower():
                return True
        if entry.tags:
            for tag in entry.tags:
                if q in tag.lower():
                    return True
        return False

    async def search(
        self, site_id: str, query: str, limit: int = 10
    ) -> list[MemoryEntry]:
        return await self.recall(site_id, query=query, limit=limit)

    async def summarize(self, site_id: str) -> str:
        recent = await self.recall(site_id, limit=50)
        if not recent:
            return f"No episodic memory for site '{site_id}'."
        lines = []
        for entry in recent:
            ts = entry.timestamp.isoformat() if entry.timestamp else "?"
            tag_str = f" [{', '.join(entry.tags)}]" if entry.tags else ""
            content_preview = entry.content
            if isinstance(content_preview, dict):
                content_preview = json.dumps(content_preview, ensure_ascii=False)[:200]
            elif isinstance(content_preview, str) and len(content_preview) > 200:
                content_preview = content_preview[:200] + "..."
            lines.append(f"[{ts}]{tag_str} {entry.key}: {content_preview}")
        return "\n".join(lines)

    async def clear(self, site_id: str) -> None:
        path = self._site_path(site_id)
        loop = get_event_loop()
        await loop.run_in_executor(None, self._sync_clear, path)

    def _sync_clear(self, path: str) -> None:
        if os.path.exists(path):
            os.remove(path)


class SemanticMemory:
    def __init__(self, skills_dir: str | None = None) -> None:
        self._skills_dir = skills_dir or os.path.join(os.getcwd(), "data", "skills")
        os.makedirs(self._skills_dir, exist_ok=True)

    def _skill_path(self, name: str) -> str:
        sanitized = name.replace("/", "_").replace("\\", "_")
        return os.path.join(self._skills_dir, f"{sanitized}.md")

    def _index_path(self) -> str:
        return os.path.join(self._skills_dir, "_index.json")

    async def _read_index(self) -> dict[str, list[str]]:
        path = self._index_path()
        if not os.path.exists(path):
            return {}
        loop = get_event_loop()
        raw = await loop.run_in_executor(None, _sync_read, path)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}

    async def _write_index(self, index: dict[str, list[str]]) -> None:
        path = self._index_path()
        data = json.dumps(index, ensure_ascii=False, indent=2)
        await _aio_write(path, data)

    async def store_skill(
        self, name: str, content: str, tags: list[str] | None = None
    ) -> None:
        path = self._skill_path(name)
        await _aio_write(path, content)
        index = await self._read_index()
        index[name] = tags or []
        await self._write_index(index)

    async def get_skill(self, name: str) -> str | None:
        path = self._skill_path(name)
        if not os.path.exists(path):
            return None
        loop = get_event_loop()
        return await loop.run_in_executor(None, _sync_read, path)

    async def search_skills(self, query: str) -> list[dict]:
        q = query.lower()
        loop = get_event_loop()
        all_files = await loop.run_in_executor(
            None, lambda: [
                f for f in os.listdir(self._skills_dir)
                if f.endswith(".md") and f != "_index.md"
            ]
        )
        index = await self._read_index()
        results: list[dict] = []
        for fname in all_files:
            name = fname[:-3]
            path = os.path.join(self._skills_dir, fname)
            if not os.path.exists(path):
                continue
            content = await loop.run_in_executor(None, _sync_read, path)
            tags = index.get(name, [])
            if (
                q in name.lower()
                or q in content.lower()
                or any(q in t.lower() for t in tags)
            ):
                results.append({
                    "name": name,
                    "tags": tags,
                    "content": content,
                })
        return results

    async def list_skills(self, tag: str | None = None) -> list[dict]:
        index = await self._read_index()
        results: list[dict] = []
        for name, tags in index.items():
            if tag and tag not in tags:
                continue
            results.append({"name": name, "tags": tags})
        return sorted(results, key=lambda x: x["name"])

    async def delete_skill(self, name: str) -> bool:
        path = self._skill_path(name)
        loop = get_event_loop()
        exists = await loop.run_in_executor(None, lambda: os.path.exists(path))
        if not exists:
            return False
        await loop.run_in_executor(None, os.remove, path)
        index = await self._read_index()
        index.pop(name, None)
        await self._write_index(index)
        return True


class HermesMemory:
    def __init__(self, storage_dir: str | None = None) -> None:
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory(storage_dir)
        self.semantic = SemanticMemory(storage_dir)

    async def remember_command(
        self, session_id: str, site_id: str, command: str, result: dict
    ) -> None:
        self.working.set(session_id, f"cmd:{command}", result)
        entry = MemoryEntry(
            key=command,
            content=result,
            timestamp=_now(),
            ttl=3600,
            tags=["command", site_id],
        )
        await self.episodic.store(site_id, entry)

    async def get_context(self, session_id: str, site_id: str) -> dict:
        working = self.working.snapshot(session_id)
        recent = await self.episodic.recall(site_id, limit=10)
        skills = await self.semantic.search_skills(site_id)
        return {
            "working": working,
            "episodic": [_to_dict(e) for e in recent],
            "skills": skills,
        }

    async def health(self) -> dict:
        episodic_dir = self.episodic._storage_dir
        episodic_ok = os.path.isdir(episodic_dir) if episodic_dir else False
        skills_dir = self.semantic._skills_dir
        skills_ok = os.path.isdir(skills_dir) if skills_dir else False
        return {
            "status": "healthy" if (episodic_ok or skills_ok) else "degraded",
            "episodic_storage": "ok" if episodic_ok else "unavailable",
            "skills_storage": "ok" if skills_ok else "unavailable",
            "working_memory_keys": sum(len(s) for s in self.working._store.values()),
        }
