import pytest
from uuid import uuid4

from app.services.semantic.models import EntityNode, EntityEdge, EntityGraph
from app.services.semantic.db import SemanticDB


class TestEntityNode:
    def test_creation(self):
        node = EntityNode(id="e1", label="Homepage", type="page")
        assert node.id == "e1"
        assert node.label == "Homepage"
        assert node.type == "page"
        assert node.properties == {}
        assert node.embedding is None

    def test_with_all_fields(self):
        node = EntityNode(
            id="e2", label="SEO", type="keyword",
            properties={"volume": 1000}, embedding=[0.1, 0.2],
        )
        assert node.properties["volume"] == 1000
        assert node.embedding == [0.1, 0.2]


class TestEntityEdge:
    def test_creation(self):
        edge = EntityEdge(source="e1", target="e2", relation="links_to")
        assert edge.source == "e1"
        assert edge.target == "e2"
        assert edge.relation == "links_to"
        assert edge.weight == 1.0
        assert edge.properties == {}

    def test_with_all_fields(self):
        edge = EntityEdge(
            source="a", target="b", relation="references",
            weight=0.8, properties={"verified": True},
        )
        assert edge.weight == 0.8
        assert edge.properties["verified"] is True


class TestEntityGraph:
    def test_creation(self):
        graph = EntityGraph(site_id="s1")
        assert graph.site_id == "s1"
        assert graph.nodes == []
        assert graph.edges == []

    def test_add_node(self):
        graph = EntityGraph(site_id="s1")
        n1 = EntityNode(id="n1", label="Page", type="page")
        graph.add_node(n1)
        assert len(graph.nodes) == 1
        graph.add_node(n1)
        assert len(graph.nodes) == 1

    def test_add_edge(self):
        graph = EntityGraph(site_id="s1")
        edge = EntityEdge(source="n1", target="n2", relation="links")
        graph.add_edge(edge)
        assert len(graph.edges) == 1

    def test_get_node(self):
        graph = EntityGraph(site_id="s1")
        n1 = EntityNode(id="n1", label="Page", type="page")
        graph.add_node(n1)
        assert graph.get_node("n1") is n1
        assert graph.get_node("nonexistent") is None

    def test_to_dict(self):
        graph = EntityGraph(site_id="s1")
        graph.add_node(EntityNode(id="n1", label="Page", type="page"))
        graph.add_edge(EntityEdge(source="n1", target="n2", relation="links"))
        d = graph.to_dict()
        assert d["site_id"] == "s1"
        assert len(d["nodes"]) == 1
        assert len(d["edges"]) == 1
        assert d["nodes"][0]["label"] == "Page"
        assert d["edges"][0]["relation"] == "links"


class TestSemanticDB:
    @pytest.fixture
    def db(self):
        return SemanticDB(dimension=32)

    @pytest.mark.asyncio
    async def test_store_and_get_entity_graph(self, db):
        node = EntityNode(id="n1", label="Homepage", type="page", embedding=[0.1] * 32)
        edge = EntityEdge(source="n1", target="n2", relation="links")
        graph = EntityGraph(site_id="site_1", nodes=[node], edges=[edge])
        await db.store_entity_graph("site_1", graph)
        retrieved = await db.get_entity_graph("site_1")
        assert retrieved is not None
        assert retrieved.site_id == "site_1"
        assert len(retrieved.nodes) == 1
        assert retrieved.nodes[0].label == "Homepage"
        assert len(retrieved.edges) == 1

    @pytest.mark.asyncio
    async def test_get_graph_alias(self, db):
        graph = EntityGraph(site_id="s1")
        await db.store_entity_graph("s1", graph)
        assert await db.get_graph("s1") is not None
        assert await db.get_graph("nonexistent") is None

    @pytest.mark.asyncio
    async def test_search_similar(self, db):
        n1 = EntityNode(id="n1", label="A", type="t", embedding=[1.0] * 32)
        n2 = EntityNode(id="n2", label="B", type="t", embedding=[0.0] * 32)
        await db.store_entity_graph("site_1", EntityGraph(site_id="site_1", nodes=[n1, n2]))
        results = await db.search_similar([1.0] * 32, limit=5)
        assert len(results) >= 1
        assert results[0]["site_id"] == "site_1"

    @pytest.mark.asyncio
    async def test_find_related_sites(self, db):
        n1 = EntityNode(id="n1", label="A", type="t", embedding=[1.0] * 32)
        n2 = EntityNode(id="n2", label="B", type="t", embedding=[0.9] * 32)
        await db.store_entity_graph("site_a", EntityGraph(site_id="site_a", nodes=[n1]))
        await db.store_entity_graph("site_b", EntityGraph(site_id="site_b", nodes=[n2]))
        related = await db.find_related_sites("site_a", max_results=5)
        assert len(related) >= 1
        assert related[0]["site_id"] == "site_b"

    @pytest.mark.asyncio
    async def test_find_similar_sites(self, db):
        await db.store_entity_graph("s1", EntityGraph(
            site_id="s1",
            nodes=[EntityNode(id="n1", label="X", type="t", embedding=[1.0] * 32)],
        ))
        await db.store_entity_graph("s2", EntityGraph(
            site_id="s2",
            nodes=[EntityNode(id="n2", label="Y", type="t", embedding=[0.5] * 32)],
        ))
        similar = await db.find_similar_sites("s1", limit=5)
        assert len(similar) >= 1

    @pytest.mark.asyncio
    async def test_get_graph_context(self, db):
        node = EntityNode(id="n1", label="SEO Tips", type="article", embedding=[0.5] * 32)
        edge = EntityEdge(source="n1", target="n2", relation="related")
        graph = EntityGraph(site_id="s1", nodes=[node], edges=[edge])
        await db.store_entity_graph("s1", graph)
        ctx = await db.get_graph_context("s1", "SEO")
        assert ctx["site_id"] == "s1"
        assert "entities" in ctx
        assert "edges" in ctx

    @pytest.mark.asyncio
    async def test_store_document(self, db):
        await db.store_document("s1", "doc1", "content")
        assert db._documents["s1"]["doc1"] == "content"

    @pytest.mark.asyncio
    async def test_get_all_site_ids(self, db):
        await db.store_entity_graph("s1", EntityGraph(site_id="s1"))
        await db.store_entity_graph("s2", EntityGraph(site_id="s2"))
        ids = await db.get_all_site_ids()
        assert "s1" in ids
        assert "s2" in ids

    @pytest.mark.asyncio
    async def test_health(self, db):
        health = await db.health()
        assert "status" in health

    @pytest.mark.asyncio
    async def test_close(self, db):
        await db.store_entity_graph("s1", EntityGraph(site_id="s1"))
        await db.close()
        assert len(db._graphs) == 0
