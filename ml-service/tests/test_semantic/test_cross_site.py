import pytest

from app.semantic.cross_site import Pattern, CrossSiteAnalyzer
from app.semantic.db import SemanticDB
from app.semantic.models import EntityNode, EntityGraph


class TestPattern:
    def test_creation(self):
        p = Pattern(
            pattern_id="p1", name="test", description="desc",
            site_count=3, avg_improvement=0.75,
        )
        assert p.pattern_id == "p1"
        assert p.site_count == 3
        assert p.avg_improvement == 0.75
        assert p.entities_involved == []
        assert p.action_sequence == []

    def test_to_dict(self):
        p = Pattern(
            pattern_id="p1", name="topic_cluster", description="desc",
            site_count=5, avg_improvement=0.85,
            entities_involved=["SEO", "Content"],
            action_sequence=["fix_title"],
        )
        d = p.to_dict()
        assert d["pattern_id"] == "p1"
        assert d["avg_improvement"] == 0.85
        assert len(d["entities_involved"]) == 2
        assert d["action_sequence"] == ["fix_title"]


class TestCrossSiteAnalyzer:
    @pytest.fixture
    def db(self):
        return SemanticDB(dimension=32)

    @pytest.fixture
    def analyzer(self, db):
        return CrossSiteAnalyzer(semantic_db=db, min_sites=2)

    def test_init(self, analyzer):
        assert analyzer.min_sites == 2
        assert analyzer._cached_patterns == []

    @pytest.mark.asyncio
    async def test_find_patterns_returns_list(self, analyzer, db):
        n1 = EntityNode(id="n1", label="SEO", type="topic", embedding=[0.5] * 32)
        n2 = EntityNode(id="n2", label="SEO", type="topic", embedding=[0.5] * 32)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[n1]))
        await db.store_entity_graph("s2", EntityGraph(site_id="s2", nodes=[n2]))
        patterns = await analyzer.find_patterns(limit=10)
        assert isinstance(patterns, list)

    @pytest.mark.asyncio
    async def test_find_patterns_few_sites(self, analyzer, db):
        await db.store_entity_graph("s1", EntityGraph(site_id="s1"))
        patterns = await analyzer.find_patterns()
        assert patterns == []

    @pytest.mark.asyncio
    async def test_get_site_cluster(self, analyzer, db):
        n1 = EntityNode(id="n1", label="A", type="t", embedding=[1.0] * 32)
        n2 = EntityNode(id="n2", label="B", type="t", embedding=[0.8] * 32)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[n1]))
        await db.store_entity_graph("s2", EntityGraph(site_id="s2", nodes=[n2]))
        cluster = await analyzer.get_site_cluster("s1")
        assert "s1" in cluster

    @pytest.mark.asyncio
    async def test_detect_action_patterns(self, analyzer):
        trajectories = [
            [{"action": "fix_title", "reward": 1.0}, {"action": "add_meta", "reward": 0.5}],
            [{"action": "fix_title", "reward": 0.8}],
            [{"action": "fix_title", "reward": 0.9}, {"action": "add_meta", "reward": 0.3}],
        ]
        patterns = await analyzer.detect_action_patterns(trajectories)
        assert len(patterns) > 0
        assert all(isinstance(p, Pattern) for p in patterns)

    @pytest.mark.asyncio
    async def test_detect_action_patterns_empty(self, analyzer):
        patterns = await analyzer.detect_action_patterns([])
        assert patterns == []

    @pytest.mark.asyncio
    async def test_get_insights_for_site(self, analyzer, db):
        n1 = EntityNode(id="n1", label="Topic", type="topic", embedding=[0.5] * 32)
        n2 = EntityNode(id="n2", label="Topic", type="topic", embedding=[0.5] * 32)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[n1]))
        await db.store_entity_graph("s2", EntityGraph(site_id="s2", nodes=[n2]))
        insights = await analyzer.get_insights_for_site("s1")
        assert isinstance(insights, list)

    @pytest.mark.asyncio
    async def test_cluster_sites_empty(self, analyzer):
        clusters = await analyzer._cluster_sites([])
        assert clusters == []

    @pytest.mark.asyncio
    async def test_cluster_sites_one(self, analyzer, db):
        await db.store_entity_graph("s1", EntityGraph(site_id="s1"))
        clusters = await analyzer._cluster_sites(["s1"])
        assert clusters == []

    @pytest.mark.asyncio
    async def test_cluster_sites_two_similar(self, analyzer, db):
        n1 = EntityNode(id="n1", label="SEO", type="topic", embedding=[0.5] * 32)
        n2 = EntityNode(id="n2", label="SEO", type="topic", embedding=[0.5] * 32)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[n1]))
        await db.store_entity_graph("s2", EntityGraph(site_id="s2", nodes=[n2]))
        clusters = await analyzer._cluster_sites(["s1", "s2"])
        assert len(clusters) == 1
        assert "s1" in clusters[0]
        assert "s2" in clusters[0]

    @pytest.mark.asyncio
    async def test_cluster_sites_five(self, analyzer, db):
        for i in range(5):
            n = EntityNode(
                id=f"n{i}", label=f"Label{i}", type="topic",
                embedding=[0.5 + i * 0.1] * 32,
            )
            await db.store_entity_graph(
                f"s{i}", EntityGraph(site_id=f"s{i}", nodes=[n])
            )
        clusters = await analyzer._cluster_sites(["s0", "s1", "s2", "s3", "s4"])
        assert len(clusters) >= 1
        total = sum(len(c) for c in clusters)
        assert total == 5

    @pytest.mark.asyncio
    async def test_extract_cluster_patterns_similar(self, analyzer, db):
        n1 = EntityNode(id="n1", label="SEO Guide", type="article",
                        embedding=[0.5] * 32)
        n2 = EntityNode(id="n2", label="SEO Guide", type="article",
                        embedding=[0.5] * 32)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[n1]))
        await db.store_entity_graph("s2", EntityGraph(site_id="s2", nodes=[n2]))
        patterns = await analyzer._extract_cluster_patterns(["s1", "s2"])
        assert len(patterns) >= 1
        assert "SEO Guide" in patterns[0].entities_involved

    @pytest.mark.asyncio
    async def test_extract_cluster_patterns_dissimilar(self, analyzer, db):
        n1 = EntityNode(id="n1", label="Cooking", type="topic",
                        embedding=[1.0] + [0.0] * 31)
        n2 = EntityNode(id="n2", label="Rockets", type="topic",
                        embedding=[0.0] * 16 + [1.0] + [0.0] * 15)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[n1]))
        await db.store_entity_graph("s2", EntityGraph(site_id="s2", nodes=[n2]))
        patterns = await analyzer._extract_cluster_patterns(["s1", "s2"])
        assert patterns == []

    @pytest.mark.asyncio
    async def test_detect_action_patterns_preserves_temporal_order(self, analyzer):
        trajectories = [
            [
                {"action": "add_meta", "reward": 0.3},
                {"action": "fix_title", "reward": 1.0},
            ],
            [
                {"action": "add_meta", "reward": 0.2},
                {"action": "fix_title", "reward": 0.9},
            ],
        ]
        patterns = await analyzer.detect_action_patterns(trajectories)
        assert len(patterns) >= 1
        seq = patterns[0].action_sequence
        assert seq[0] == "add_meta"
        assert seq[1] == "fix_title"

    @pytest.mark.asyncio
    async def test_find_patterns_end_to_end(self, analyzer, db):
        n1 = EntityNode(id="n1", label="Content", type="article",
                        embedding=[0.5] * 32)
        n2 = EntityNode(id="n2", label="Content", type="article",
                        embedding=[0.5] * 32)
        n3 = EntityNode(id="n3", label="Content", type="article",
                        embedding=[0.5] * 32)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[n1]))
        await db.store_entity_graph("s2", EntityGraph(site_id="s2", nodes=[n2]))
        await db.store_entity_graph("s3", EntityGraph(site_id="s3", nodes=[n3]))
        patterns = await analyzer.find_patterns(limit=10)
        assert len(patterns) >= 1
        assert all(isinstance(p, Pattern) for p in patterns)

    @pytest.mark.asyncio
    async def test_all_identical_sites(self, analyzer, db):
        for i in range(3):
            n = EntityNode(
                id=f"n{i}", label="SEO", type="topic",
                embedding=[0.5] * 32,
            )
            await db.store_entity_graph(
                f"s{i}", EntityGraph(site_id=f"s{i}", nodes=[n])
            )
        patterns = await analyzer.find_patterns()
        assert len(patterns) >= 1

    @pytest.mark.asyncio
    async def test_all_different_sites(self, analyzer, db):
        labels = ["Cooking", "Rockets", "Medicine", "Music", "Sports"]
        for i, label in enumerate(labels):
            n = EntityNode(
                id=f"n{i}", label=label, type="topic",
                embedding=[0.1 + i * 0.2] * 32,
            )
            await db.store_entity_graph(
                f"s{i}", EntityGraph(site_id=f"s{i}", nodes=[n])
            )
        patterns = await analyzer.find_patterns()
        assert isinstance(patterns, list)

    @pytest.mark.asyncio
    async def test_get_insights_for_site_with_cached_patterns(self, analyzer, db):
        n1 = EntityNode(id="n1", label="Topic", type="topic",
                        embedding=[0.5] * 32)
        n2 = EntityNode(id="n2", label="Topic", type="topic",
                        embedding=[0.5] * 32)
        await db.store_entity_graph("s1", EntityGraph(site_id="s1", nodes=[n1]))
        await db.store_entity_graph("s2", EntityGraph(site_id="s2", nodes=[n2]))
        await analyzer.find_patterns()
        insights = await analyzer.get_insights_for_site("s1")
        assert isinstance(insights, list)
