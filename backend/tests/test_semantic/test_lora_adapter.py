import torch
import pytest
import os
from unittest.mock import AsyncMock, patch

from app.services.semantic.models import LoRAContext, EntityNode, EntityGraph
from app.services.semantic.lora import LoRASemanticAdapter, LoRAModule
from app.services.semantic.db import SemanticDB


class TestLoRAModule:
    def test_forward_shape_preservation(self):
        module = LoRAModule(in_dim=32, rank=8)
        x = torch.randn(4, 32)
        out = module(x)
        assert out.shape == (4, 32)

    def test_low_rank_decomposition(self):
        module = LoRAModule(in_dim=64, rank=4)
        assert module.lora_a.shape == (64, 4)
        assert module.lora_b.shape == (4, 64)
        assert module.rank == 4

    def test_forward_with_batch_maintains_shape(self):
        module = LoRAModule(in_dim=16, rank=4)
        x = torch.randn(2, 16)
        out = module(x)
        assert out.shape == (2, 16)

    def test_forward_differs_after_training(self):
        module = LoRAModule(in_dim=16, rank=4)
        x = torch.randn(2, 16)
        out_before = module(x)
        with torch.no_grad():
            module.lora_b.data = torch.randn(4, 16) * 0.1
        out_after = module(x)
        assert not torch.equal(out_before, out_after)

    def test_initial_forward_close_to_identity(self):
        module = LoRAModule(in_dim=32, rank=8)
        x = torch.randn(4, 32)
        out = module(x)
        diff = (out - x).abs().mean().item()
        assert diff < 0.1

    def test_parameter_count(self):
        module = LoRAModule(in_dim=32, rank=8)
        total = module.lora_a.numel() + module.lora_b.numel()
        assert module.parameter_count == total
        assert module.parameter_count == 512

    def test_different_rank_sizes(self):
        module = LoRAModule(in_dim=128, rank=2)
        assert module.lora_a.shape == (128, 2)
        assert module.lora_b.shape == (2, 128)
        x = torch.randn(1, 128)
        out = module(x)
        assert out.shape == (1, 128)


class TestLoRASemanticAdapter:
    @pytest.fixture
    def db(self):
        return SemanticDB(dimension=32)

    @pytest.fixture
    def adapter(self, db):
        return LoRASemanticAdapter(semantic_db=db, rank=8, alpha=0.5)

    def test_init(self, adapter):
        assert adapter.rank == 8
        assert adapter.alpha == 0.5

    @pytest.mark.asyncio
    async def test_adapt_returns_context(self, adapter, db):
        node = EntityNode(id="n1", label="SEO Guide", type="article",
                          embedding=[0.5] * 32)
        graph = EntityGraph(site_id="s1", nodes=[node])
        await db.store_entity_graph("s1", graph)
        ctx = await adapter.adapt("s1", "search engine optimization")
        assert isinstance(ctx, LoRAContext)
        assert ctx.site_id == "s1"
        assert ctx.query == "search engine optimization"
        assert len(ctx.adapted_embedding) == 384
        assert ctx.confidence > 0

    @pytest.mark.asyncio
    async def test_adapt_with_none_graph(self, adapter, db):
        ctx = await adapter.adapt("nonexistent", "test")
        assert isinstance(ctx, LoRAContext)
        assert ctx.confidence == 0.0
        assert ctx.top_entities == []

    @pytest.mark.asyncio
    async def test_get_adapter(self, adapter, db):
        ctx = await adapter.adapt("s1", "test")
        retrieved = await adapter.get_adapter(ctx.adapter_id)
        assert retrieved is not None
        assert retrieved.adapter_id == ctx.adapter_id
        assert await adapter.get_adapter("invalid") is None

    @pytest.mark.asyncio
    async def test_list_adapters(self, adapter, db):
        await adapter.adapt("s1", "q1")
        await adapter.adapt("s1", "q2")
        await adapter.adapt("s2", "q3")
        all_adapters = await adapter.list_adapters()
        assert len(all_adapters) == 3
        site_adapters = await adapter.list_adapters(site_id="s1")
        assert len(site_adapters) == 2
        assert all(a.site_id == "s1" for a in site_adapters)

    @pytest.mark.asyncio
    async def test_adapt_uses_site_vector(self, adapter, db):
        node = EntityNode(id="n1", label="Content", type="article",
                          embedding=[0.8] * 32)
        graph = type("EntityGraph", (), {
            "site_id": "s1", "nodes": [node], "edges": [],
        })()
        await db.store_entity_graph("s1", graph)
        ctx1 = await adapter.adapt("s1", "optimization")
        ctx2 = await adapter.adapt("s1", "marketing")
        assert ctx1.adapter_id != ctx2.adapter_id

    @pytest.mark.asyncio
    async def test_adapt_multiple_calls_same_site(self, adapter, db):
        node = EntityNode(id="n1", label="SEO", type="topic",
                          embedding=[0.5] * 32)
        graph = EntityGraph(site_id="s1", nodes=[node])
        await db.store_entity_graph("s1", graph)
        ctx1 = await adapter.adapt("s1", "optimization")
        ctx2 = await adapter.adapt("s1", "content strategy")
        assert ctx1.adapter_id != ctx2.adapter_id
        assert all(isinstance(c.adapted_embedding, list) for c in [ctx1, ctx2])

    @pytest.mark.asyncio
    async def test_adapt_unknown_site_without_graph(self, adapter):
        ctx = await adapter.adapt("unknown", "test query")
        assert isinstance(ctx, LoRAContext)
        assert ctx.confidence == 0.0
        assert ctx.top_entities == []

    @pytest.mark.asyncio
    async def test_train_step_positive_reward(self, adapter, db):
        node = EntityNode(id="n1", label="SEO Guide", type="article",
                          embedding=[0.5] * 32)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[node]))
        result = await adapter.train_step("s1", "optimization", reward=1.0)
        assert isinstance(result, dict)
        assert "loss" in result
        assert "reward" in result
        assert result["reward"] == 1.0

    @pytest.mark.asyncio
    async def test_train_step_negative_reward(self, adapter, db):
        node = EntityNode(id="n1", label="SEO Guide", type="article",
                          embedding=[0.5] * 32)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[node]))
        result = await adapter.train_step("s1", "optimization", reward=-1.0)
        assert isinstance(result, dict)
        assert "loss" in result
        assert result["reward"] == -1.0

    @pytest.mark.asyncio
    async def test_train_step_zero_reward(self, adapter, db):
        node = EntityNode(id="n1", label="SEO Guide", type="article",
                          embedding=[0.5] * 32)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[node]))
        result = await adapter.train_step("s1", "optimization", reward=0.0)
        assert isinstance(result, dict)
        assert "loss" in result

    @pytest.mark.asyncio
    async def test_train_step_without_graph(self, adapter):
        result = await adapter.train_step("unknown", "test", reward=0.5)
        assert isinstance(result, dict)
        assert "loss" in result
        assert "reward" in result

    def test_save_and_load_persistence(self, adapter, tmp_path):
        lora = LoRAModule(in_dim=32, rank=8)
        adapter._lora_modules["s1"] = lora

        path = os.path.join(str(tmp_path), "lora.pt")
        adapter.save(path)

        adapter2 = LoRASemanticAdapter(
            semantic_db=SemanticDB(dimension=32), rank=8, alpha=0.5
        )
        adapter2.load(path)

        assert "s1" in adapter2._lora_modules
        w1 = dict(adapter._lora_modules["s1"].named_parameters())
        w2 = dict(adapter2._lora_modules["s1"].named_parameters())
        for key in w1:
            assert torch.equal(w1[key], w2[key]), f"Mismatch in {key}"

    def test_save_load_empty(self, adapter, tmp_path):
        path = os.path.join(str(tmp_path), "empty_lora.pt")
        adapter.save(path)

        adapter2 = LoRASemanticAdapter(
            semantic_db=SemanticDB(dimension=32), rank=8, alpha=0.5
        )
        adapter2.load(path)
        assert len(adapter2._lora_modules) == 0

    def test_save_load_multiple_sites(self, adapter, tmp_path):
        adapter._lora_modules["s1"] = LoRAModule(in_dim=32, rank=8)
        adapter._lora_modules["s2"] = LoRAModule(in_dim=32, rank=8)

        path = os.path.join(str(tmp_path), "multi_lora.pt")
        adapter.save(path)

        adapter2 = LoRASemanticAdapter(
            semantic_db=SemanticDB(dimension=32), rank=8, alpha=0.5
        )
        adapter2.load(path)

        assert len(adapter2._lora_modules) == 2
        assert "s1" in adapter2._lora_modules
        assert "s2" in adapter2._lora_modules

    @pytest.mark.asyncio
    async def test_train_step_creates_lora_module(self, adapter, db):
        node = EntityNode(id="n1", label="SEO", type="topic",
                          embedding=[0.5] * 32)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[node]))
        assert "s1" not in adapter._lora_modules
        await adapter.train_step("s1", "test", reward=0.5)
        assert "s1" in adapter._lora_modules
        assert isinstance(adapter._lora_modules["s1"], LoRAModule)

    @pytest.mark.asyncio
    async def test_train_step_accumulates_updates(self, adapter, db):
        node = EntityNode(id="n1", label="SEO", type="topic",
                          embedding=[0.5] * 32)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[node]))
        result1 = await adapter.train_step("s1", "test", reward=1.0, lr=0.1)
        result2 = await adapter.train_step("s1", "test", reward=1.0, lr=0.1)
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
