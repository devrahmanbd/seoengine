import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.api.v1.growth import router as growth_router
from app.services.growth.growth_tracker import GrowthState


@pytest.fixture
def app():
    a = FastAPI()
    a.include_router(growth_router)
    return a


@pytest.fixture
def mock_tracker():
    tracker = MagicMock()
    tracker.get_growth_state = AsyncMock(return_value=GrowthState(
        website_id="site-1", growth_score=0.65, trend="accelerating",
        trajectory_count=5, avg_reward=0.65,
        score_history=[50, 60, 70, 75, 80],
        action_effectiveness={"fix_title": {"count": 3, "avg_reward": 0.8}},
    ))
    tracker.compare_websites = AsyncMock(return_value=[
        GrowthState(website_id="site-1", growth_score=0.8, trend="accelerating", trajectory_count=5, avg_reward=0.8),
        GrowthState(website_id="site-2", growth_score=0.3, trend="declining", trajectory_count=2, avg_reward=0.3),
    ])
    tracker.needs_intervention = AsyncMock(return_value=False)
    tracker.get_effective_actions = AsyncMock(return_value={
        "fix_title": {"count": 3, "avg_reward": 0.8},
    })
    return tracker


class TestGrowthAPI:
    @pytest.mark.asyncio
    async def test_get_growth_state(self, app, mock_tracker):
        with patch("app.api.v1.growth.growth_tracker", mock_tracker):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/admin/v1/growth/site-1")
                assert resp.status_code == 200
                data = resp.json()
                assert data["website_id"] == "site-1"
                assert data["growth_score"] == 0.65
                assert data["trend"] == "accelerating"
                assert len(data["score_history"]) == 5

    @pytest.mark.asyncio
    async def test_get_growth_state_not_found(self, app):
        mock = MagicMock()
        mock.get_growth_state = AsyncMock(return_value=GrowthState(
            website_id="unknown", growth_score=0.0, trend="unknown",
            trajectory_count=0, avg_reward=0.0,
        ))
        with patch("app.api.v1.growth.growth_tracker", mock):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/admin/v1/growth/unknown")
                assert resp.status_code == 200
                assert resp.json()["trajectory_count"] == 0

    @pytest.mark.asyncio
    async def test_compare_websites(self, app, mock_tracker):
        with patch("app.api.v1.growth.growth_tracker", mock_tracker):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/admin/v1/growth/compare", json={"website_ids": ["site-1", "site-2"]})
                assert resp.status_code == 200
                data = resp.json()
                assert len(data) == 2
                assert data[0]["website_id"] == "site-1"

    @pytest.mark.asyncio
    async def test_compare_empty(self, app, mock_tracker):
        mock_tracker.compare_websites = AsyncMock(return_value=[])
        with patch("app.api.v1.growth.growth_tracker", mock_tracker):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/admin/v1/growth/compare", json={"website_ids": []})
                assert resp.status_code == 200
                assert resp.json() == []

    @pytest.mark.asyncio
    async def test_intervention_check(self, app, mock_tracker):
        with patch("app.api.v1.growth.growth_tracker", mock_tracker):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/admin/v1/growth/site-1/intervention")
                assert resp.status_code == 200
                assert resp.json()["needs_intervention"] is False

    @pytest.mark.asyncio
    async def test_effective_actions(self, app, mock_tracker):
        with patch("app.api.v1.growth.growth_tracker", mock_tracker):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/admin/v1/growth/site-1/effective-actions")
                assert resp.status_code == 200
                assert "fix_title" in resp.json()

    @pytest.mark.asyncio
    async def test_opportunities_endpoint(self, app):
        mock_opp = MagicMock()
        mock_opp.detect_opportunities = AsyncMock(return_value=[
            MagicMock(
                action_type="fix_title", expected_reward=0.85, confidence="high",
                source="policy", effort="low", description="Fix the title",
                evidence=["Policy confidence: 0.85"],
            ),
        ])
        with patch("app.api.v1.growth.opportunity_detector", mock_opp):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/admin/v1/growth/site-1/opportunities",
                    json={"score": 55, "issues": 5},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert len(data) == 1
                assert data[0]["action_type"] == "fix_title"

    @pytest.mark.asyncio
    async def test_schedule_endpoint(self, app):
        from datetime import datetime, timezone
        mock_opp = MagicMock()
        mock_opp.detect_opportunities = AsyncMock(return_value=[
            MagicMock(
                action_type="fix_title", expected_reward=0.85, confidence="high",
                source="policy", effort="low", description="Fix the title",
                evidence=[],
            ),
        ])
        mock_sched = MagicMock()
        mock_sched.schedule = MagicMock(return_value=[
            MagicMock(
                opportunity=MagicMock(
                    action_type="fix_title", expected_reward=0.85, confidence="high",
                    source="policy", effort="low", description="Fix the title",
                    evidence=[],
                ),
                priority_score=1.7, scheduled_at=datetime.now(timezone.utc), status="pending",
            ),
        ])
        with (
            patch("app.api.v1.growth.opportunity_detector", mock_opp),
            patch("app.api.v1.growth.action_scheduler", mock_sched),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/admin/v1/growth/site-1/schedule",
                    json={"score": 55, "issues": 5, "max_actions": 5},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert len(data) == 1
                assert data[0]["action_type"] == "fix_title"
                assert data[0]["priority_score"] == 1.7
