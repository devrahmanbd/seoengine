import os
import json
import tempfile
import pytest

from app.services.hermes import (
    MemoryEntry,
    WorkingMemory,
    EpisodicMemory,
    SemanticMemory,
    HermesMemory,
)


class TestMemoryEntry:
    def test_creation(self):
        e = MemoryEntry(key="test", content="value")
        assert e.key == "test"
        assert e.content == "value"
        assert e.timestamp is None
        assert e.ttl is None
        assert e.tags is None

    def test_with_all_fields(self):
        e = MemoryEntry(
            key="k1",
            content={"nested": "data"},
            tags=["tag1", "tag2"],
            ttl=3600,
        )
        assert e.content == {"nested": "data"}
        assert e.tags == ["tag1", "tag2"]
        assert e.ttl == 3600


class TestWorkingMemory:
    @pytest.fixture
    def wm(self):
        return WorkingMemory()

    def test_set_and_get(self, wm):
        wm.set("s1", "key1", "value1")
        assert wm.get("s1", "key1") == "value1"

    def test_get_default(self, wm):
        assert wm.get("s1", "missing") is None
        assert wm.get("s1", "missing", "default") == "default"

    def test_delete(self, wm):
        wm.set("s1", "key1", "value1")
        wm.delete("s1", "key1")
        assert wm.get("s1", "key1") is None

    def test_clear_session(self, wm):
        wm.set("s1", "a", 1)
        wm.set("s1", "b", 2)
        wm.clear_session("s1")
        assert wm.get("s1", "a") is None
        assert wm.get("s1", "b") is None

    def test_isolation_between_sessions(self, wm):
        wm.set("s1", "key", "val1")
        wm.set("s2", "key", "val2")
        assert wm.get("s1", "key") == "val1"
        assert wm.get("s2", "key") == "val2"

    def test_snapshot(self, wm):
        wm.set("s1", "x", 10)
        wm.set("s1", "y", 20)
        snap = wm.snapshot("s1")
        assert snap == {"x": 10, "y": 20}

    def test_snapshot_is_copy(self, wm):
        wm.set("s1", "x", 10)
        snap = wm.snapshot("s1")
        snap["x"] = 99
        assert wm.get("s1", "x") == 10


class TestEpisodicMemory:
    @pytest.fixture
    def storage_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mem(self, storage_dir):
        return EpisodicMemory(storage_dir)

    @pytest.mark.asyncio
    async def test_store_and_recall(self, mem):
        entry = MemoryEntry(key="cmd1", content="result1", tags=["test"])
        await mem.store("site1", entry)
        results = await mem.recall("site1")
        assert len(results) == 1
        assert results[0].key == "cmd1"
        assert results[0].content == "result1"

    @pytest.mark.asyncio
    async def test_recall_empty_site(self, mem):
        results = await mem.recall("nonexistent")
        assert results == []

    @pytest.mark.asyncio
    async def test_recall_with_query(self, mem):
        e1 = MemoryEntry(key="cmd1", content="seo analysis done", tags=["seo"])
        e2 = MemoryEntry(key="cmd2", content="backlink check", tags=["links"])
        await mem.store("site1", e1)
        await mem.store("site1", e2)
        results = await mem.recall("site1", query="seo")
        assert len(results) == 1
        assert results[0].key == "cmd1"

    @pytest.mark.asyncio
    async def test_search_delegates_to_recall(self, mem):
        entry = MemoryEntry(key="k1", content="content")
        await mem.store("site1", entry)
        results = await mem.search("site1", "content")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_recall_limit(self, mem):
        for i in range(10):
            await mem.store("site1", MemoryEntry(key=f"k{i}", content=f"v{i}"))
        results = await mem.recall("site1", limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_recall_returns_most_recent_first(self, mem):
        entries = []
        for i in range(5):
            e = MemoryEntry(key=f"k{i}", content=f"v{i}")
            await mem.store("site1", e)
            entries.append(e)
        results = await mem.recall("site1", limit=5)
        timestamps = [r.timestamp for r in results if r.timestamp]
        assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_recall_filters_expired_entries(self, mem):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        e1 = MemoryEntry(
            key="expired", content="old data",
            ttl=1, timestamp=now - timedelta(seconds=2),
        )
        e2 = MemoryEntry(
            key="valid", content="new data", ttl=3600,
            timestamp=now,
        )
        await mem.store("site1", e1)
        await mem.store("site1", e2)
        results = await mem.recall("site1")
        keys = [r.key for r in results]
        assert "expired" not in keys
        assert "valid" in keys

    @pytest.mark.asyncio
    async def test_recall_keeps_entries_without_ttl(self, mem):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        e1 = MemoryEntry(
            key="no_ttl", content="persistent",
            timestamp=now - timedelta(days=30),
        )
        e2 = MemoryEntry(
            key="with_ttl", content="fresh", ttl=3600,
            timestamp=now,
        )
        await mem.store("site1", e1)
        await mem.store("site1", e2)
        results = await mem.recall("site1")
        keys = [r.key for r in results]
        assert "no_ttl" in keys
        assert "with_ttl" in keys
    @pytest.fixture
    def storage_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mem(self, storage_dir):
        return EpisodicMemory(storage_dir)

    @pytest.mark.asyncio
    async def test_store_and_recall(self, mem):
        entry = MemoryEntry(key="cmd1", content="result1", tags=["test"])
        await mem.store("site1", entry)
        results = await mem.recall("site1")
        assert len(results) == 1
        assert results[0].key == "cmd1"
        assert results[0].content == "result1"

    @pytest.mark.asyncio
    async def test_recall_empty_site(self, mem):
        results = await mem.recall("nonexistent")
        assert results == []

    @pytest.mark.asyncio
    async def test_recall_with_query(self, mem):
        e1 = MemoryEntry(key="cmd1", content="seo analysis done", tags=["seo"])
        e2 = MemoryEntry(key="cmd2", content="backlink check", tags=["links"])
        await mem.store("site1", e1)
        await mem.store("site1", e2)
        results = await mem.recall("site1", query="seo")
        assert len(results) == 1
        assert results[0].key == "cmd1"

    @pytest.mark.asyncio
    async def test_search_delegates_to_recall(self, mem):
        entry = MemoryEntry(key="k1", content="content")
        await mem.store("site1", entry)
        results = await mem.search("site1", "content")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_recall_limit(self, mem):
        for i in range(10):
            await mem.store("site1", MemoryEntry(key=f"k{i}", content=f"v{i}"))
        results = await mem.recall("site1", limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_recall_returns_most_recent_first(self, mem):
        entries = []
        for i in range(5):
            e = MemoryEntry(key=f"k{i}", content=f"v{i}")
            await mem.store("site1", e)
            entries.append(e)
        results = await mem.recall("site1", limit=5)
        timestamps = [r.timestamp for r in results if r.timestamp]
        assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_summarize(self, mem):
        await mem.store("site1", MemoryEntry(key="k1", content="data"))
        summary = await mem.summarize("site1")
        assert "k1" in summary
        assert "data" in summary

    @pytest.mark.asyncio
    async def test_summarize_empty(self, mem):
        summary = await mem.summarize("nonexistent")
        assert "No episodic memory" in summary

    @pytest.mark.asyncio
    async def test_clear(self, mem):
        await mem.store("site1", MemoryEntry(key="k1", content="v1"))
        await mem.clear("site1")
        results = await mem.recall("site1")
        assert results == []

    @pytest.mark.asyncio
    async def test_persistence_across_instances(self, storage_dir):
        mem1 = EpisodicMemory(storage_dir)
        await mem1.store("site1", MemoryEntry(key="k1", content="v1"))
        mem2 = EpisodicMemory(storage_dir)
        results = await mem2.recall("site1")
        assert len(results) == 1
        assert results[0].key == "k1"


class TestSemanticMemory:
    @pytest.fixture
    def skills_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def sm(self, skills_dir):
        return SemanticMemory(skills_dir)

    @pytest.mark.asyncio
    async def test_store_and_get_skill(self, sm):
        await sm.store_skill("test-skill", "# Test\ncontent here", tags=["seo"])
        content = await sm.get_skill("test-skill")
        assert content is not None
        assert "content here" in content

    @pytest.mark.asyncio
    async def test_get_nonexistent_skill(self, sm):
        content = await sm.get_skill("nonexistent")
        assert content is None

    @pytest.mark.asyncio
    async def test_search_skills_by_name(self, sm):
        await sm.store_skill("seo-analysis", "# SEO", tags=["seo"])
        await sm.store_skill("backlink-check", "# Backlinks", tags=["links"])
        results = await sm.search_skills("seo")
        assert len(results) >= 1
        names = [r["name"] for r in results]
        assert "seo-analysis" in names

    @pytest.mark.asyncio
    async def test_search_skills_by_content(self, sm):
        await sm.store_skill("content-skill", "keyword research content")
        results = await sm.search_skills("keyword")
        assert len(results) >= 1
        assert results[0]["name"] == "content-skill"

    @pytest.mark.asyncio
    async def test_list_skills(self, sm):
        await sm.store_skill("skill-a", "content a", tags=["tag1"])
        await sm.store_skill("skill-b", "content b", tags=["tag2"])
        skills = await sm.list_skills()
        assert len(skills) == 2

    @pytest.mark.asyncio
    async def test_list_skills_filter_by_tag(self, sm):
        await sm.store_skill("skill-a", "content a", tags=["seo"])
        await sm.store_skill("skill-b", "content b", tags=["links"])
        skills = await sm.list_skills(tag="seo")
        assert len(skills) == 1
        assert skills[0]["name"] == "skill-a"

    @pytest.mark.asyncio
    async def test_delete_skill(self, sm):
        await sm.store_skill("delete-me", "content")
        assert await sm.get_skill("delete-me") is not None
        result = await sm.delete_skill("delete-me")
        assert result is True
        assert await sm.get_skill("delete-me") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_skill(self, sm):
        result = await sm.delete_skill("nonexistent")
        assert result is False


class TestHermesMemory:
    @pytest.fixture
    def storage_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def hm(self, storage_dir):
        return HermesMemory(storage_dir)

    @pytest.mark.asyncio
    async def test_remember_command_stores_in_working_and_episodic(self, hm):
        await hm.remember_command(
            session_id="s1",
            site_id="site1",
            command="analyze",
            result={"status": "done"},
        )
        working = hm.working.get("s1", "cmd:analyze")
        assert working == {"status": "done"}
        episodic = await hm.episodic.recall("site1")
        assert len(episodic) >= 1
        assert episodic[0].key == "analyze"

    @pytest.mark.asyncio
    async def test_get_context(self, hm):
        await hm.remember_command("s1", "site1", "cmd1", {"ok": True})
        await hm.semantic.store_skill("site1", "site-specific knowledge", tags=["site1"])
        ctx = await hm.get_context("s1", "site1")
        assert "working" in ctx
        assert "episodic" in ctx
        assert "skills" in ctx
        assert ctx["working"].get("cmd:cmd1") == {"ok": True}


class TestHermesAgentMemoryIntegration:
    @pytest.fixture
    def storage_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def agent_with_memory(self, storage_dir):
        from app.services.hermes.memory import HermesMemory
        from app.services.hermes.agent import HermesAgent
        memory = HermesMemory(storage_dir)
        agent = HermesAgent(memory=memory)
        return agent

    @pytest.mark.asyncio
    async def test_agent_memory_accessible(self, agent_with_memory):
        hm = agent_with_memory.memory
        assert hm is not None
        assert hasattr(hm, "working")
        assert hasattr(hm, "episodic")
        assert hasattr(hm, "semantic")

    @pytest.mark.asyncio
    async def test_working_memory_persists_across_commands(self, agent_with_memory):
        hm = agent_with_memory.memory
        hm.working.set("s1", "url", "https://example.com")
        val = hm.working.get("s1", "url")
        assert val == "https://example.com"
        hm.working.set("s1", "depth", 5)
        assert hm.working.get("s1", "depth") == 5
        assert hm.working.get("s1", "url") == "https://example.com"

    @pytest.mark.asyncio
    async def test_episodic_memory_persists_across_commands(self, agent_with_memory):
        from app.services.hermes.memory import MemoryEntry
        hm = agent_with_memory.memory
        await hm.episodic.store("site1", MemoryEntry(key="cmd1", content="result1"))
        await hm.episodic.store("site1", MemoryEntry(key="cmd2", content="result2"))
        results = await hm.episodic.recall("site1", limit=10)
        assert len(results) == 2
        keys = [r.key for r in results]
        assert "cmd1" in keys
        assert "cmd2" in keys

    @pytest.mark.asyncio
    async def test_semantic_memory_accessible_through_agent(self, agent_with_memory):
        hm = agent_with_memory.memory
        await hm.semantic.store_skill("test-skill", "# Test Skill", tags=["seo"])
        content = await hm.semantic.get_skill("test-skill")
        assert content is not None
        assert "# Test Skill" in content

    @pytest.mark.asyncio
    async def test_memory_persists_across_same_session_commands(self, agent_with_memory):
        hm = agent_with_memory.memory
        async def handler(input_data):
            site = input_data["session"].site_id or "default"
            await hm.remember_command(
                input_data["session"].session_id,
                site,
                input_data["args"][0] if input_data["args"] else "cmd",
                {"result": "ok"},
            )
            return "done"
        agent_with_memory.register_command("save", handler)

        sid = await agent_with_memory.create_session(site_id="testsite")
        await agent_with_memory.handle_message(sid, "save first")
        await agent_with_memory.handle_message(sid, "save second")

        working = hm.working.snapshot(sid)
        cmd_keys = [k for k in working if k.startswith("cmd:")]
        assert len(cmd_keys) >= 2

    @pytest.mark.asyncio
    async def test_get_context_returns_all_memory_types(self, agent_with_memory):
        hm = agent_with_memory.memory
        hm.working.set("s1", "current_url", "https://example.com")
        from app.services.hermes.memory import MemoryEntry
        await hm.episodic.store("site1", MemoryEntry(key="prev", content="old data"))
        await hm.semantic.store_skill("domain-knowledge", "# Domain: example.com", tags=["site1"])

        ctx = await hm.get_context("s1", "site1")
        assert "working" in ctx
        assert "episodic" in ctx
        assert "skills" in ctx
        assert ctx["working"].get("current_url") == "https://example.com"

    @pytest.mark.asyncio
    async def test_remember_command_stores_both_memory_types(self, agent_with_memory):
        hm = agent_with_memory.memory
        await hm.remember_command("s1", "site1", "analyze", {"score": 85})
        working = hm.working.get("s1", "cmd:analyze")
        assert working == {"score": 85}
        episodic = await hm.episodic.recall("site1")
        assert len(episodic) >= 1
        assert episodic[0].content == {"score": 85}
