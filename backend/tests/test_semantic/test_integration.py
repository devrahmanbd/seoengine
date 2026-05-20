import pytest
from unittest.mock import patch, MagicMock

from app.services.semantic.db import SemanticDB
from app.services.semantic.models import EntityNode, EntityGraph
from app.services.semantic.lora import LoRASemanticAdapter
from app.services.semantic.cross_site import CrossSiteAnalyzer


@pytest.fixture(autouse=True)
def mock_embeddings():
    import app.services.semantic.embeddings as emb
    emb._model = None
    with patch("app.services.semantic.embeddings._get_model") as mock_get:
        mock_model = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [0.1] * 384
        mock_get.return_value = mock_model
        yield


@pytest.fixture
def db():
    return SemanticDB(dimension=384)


@pytest.fixture
def lora(db):
    return LoRASemanticAdapter(semantic_db=db, rank=8, alpha=0.5)


@pytest.fixture
def cross(db):
    return CrossSiteAnalyzer(semantic_db=db, min_sites=2)


@pytest.mark.asyncio
async def test_pipeline_embed_store_search_adapt_analyze(db, lora, cross):
    n1 = EntityNode(id="n1", label="SEO Guide", type="article",
                    embedding=[0.5] * 384)
    n2 = EntityNode(id="n2", label="SEO Guide", type="article",
                    embedding=[0.5] * 384)
    n3 = EntityNode(id="n3", label="Content Strategy", type="article",
                    embedding=[0.4] * 384)

    await db.store_entity_graph("site_a", EntityGraph(
        site_id="site_a", nodes=[n1]))
    await db.store_entity_graph("site_b", EntityGraph(
        site_id="site_b", nodes=[n2]))
    await db.store_entity_graph("site_c", EntityGraph(
        site_id="site_c", nodes=[n3]))

    results = await db.search_similar([0.5] * 384, limit=5)
    assert len(results) >= 2
    assert all(r["site_id"] in ("site_a", "site_b", "site_c") for r in results)

    ctx = await lora.adapt("site_a", "search engine optimization")
    assert isinstance(ctx.adapted_embedding, list)
    assert len(ctx.adapted_embedding) > 0

    patterns = await cross.find_patterns(limit=10)
    assert isinstance(patterns, list)

    insights = await cross.get_insights_for_site("site_a")
    assert isinstance(insights, list)


@pytest.mark.asyncio
async def test_pipeline_single_site_returns_empty_patterns(db, lora, cross):
    n1 = EntityNode(id="n1", label="SEO", type="topic",
                    embedding=[0.5] * 384)
    await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[n1]))

    ctx = await lora.adapt("s1", "test")
    assert ctx.confidence > 0

    patterns = await cross.find_patterns()
    assert patterns == []


@pytest.mark.asyncio
async def test_pipeline_adapt_and_train(db, lora):
    n1 = EntityNode(id="n1", label="SEO Optimization", type="article",
                    embedding=[0.5] * 384)
    await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[n1]))

    ctx = await lora.adapt("s1", "SEO")
    assert ctx.confidence > 0

    result = await lora.train_step("s1", "SEO", reward=1.0)
    assert "loss" in result
    assert "reward" in result
    assert result["reward"] == 1.0

    ctx2 = await lora.adapt("s1", "SEO")
    assert len(ctx2.adapted_embedding) > 0


@pytest.mark.asyncio
async def test_pipeline_cross_site_discovery(db, lora, cross):
    for i in range(4):
        n = EntityNode(
            id=f"n{i}", label=f"Topic{i}", type="topic",
            embedding=[0.3 + i * 0.2] * 384,
        )
        await db.store_entity_graph(
            f"s{i}", EntityGraph(site_id=f"s{i}", nodes=[n])
        )

    patterns = await cross.find_patterns()
    assert isinstance(patterns, list)

    similar = await db.find_similar_sites("s0", limit=3)
    assert isinstance(similar, list)
