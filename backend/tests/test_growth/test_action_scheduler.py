import pytest
from datetime import datetime, timedelta, timezone
from app.services.growth.action_scheduler import ActionScheduler, ScheduledAction
from app.services.growth.opportunity_detector import Opportunity


@pytest.fixture
def scheduler():
    return ActionScheduler()


def make_opp(action_type: str, reward: float, confidence: str = "medium", effort: str = "medium"):
    return Opportunity(
        action_type=action_type,
        expected_reward=reward,
        confidence=confidence,
        source="policy",
        effort=effort,
        description=f"Test {action_type}",
        evidence=["test"],
    )


class TestActionScheduler:
    def test_schedule_prioritizes_by_score(self, scheduler):
        opps = [
            make_opp("fix_title", 0.9, "high", "low"),
            make_opp("build_backlinks", 0.3, "low", "high"),
            make_opp("add_schema", 0.6, "medium", "medium"),
        ]
        scheduled = scheduler.schedule(opps, max_actions=3)
        assert len(scheduled) == 3
        scores = [s.priority_score for s in scheduled]
        assert scores == sorted(scores, reverse=True)
        assert scheduled[0].opportunity.action_type == "fix_title"

    def test_respects_max_actions(self, scheduler):
        opps = [make_opp(f"action_{i}", 0.5) for i in range(10)]
        scheduled = scheduler.schedule(opps, max_actions=3)
        assert len(scheduled) == 3

    def test_high_confidence_high_reward_immediate(self, scheduler):
        opp = make_opp("fix_title", 0.95, "high", "low")
        scheduled = scheduler.schedule([opp])
        assert scheduled[0].status == "pending"

    def test_low_reward_actions_scheduled_later(self, scheduler):
        now = datetime.now(timezone.utc)
        opps = [
            make_opp("urgent", 0.8, "high", "low"),
            make_opp("low_priority", 0.1, "low", "high"),
        ]
        scheduled = scheduler.schedule(opps)
        urgent_action = next(s for s in scheduled if s.opportunity.action_type == "urgent")
        low_action = next(s for s in scheduled if s.opportunity.action_type == "low_priority")
        if urgent_action.scheduled_at and low_action.scheduled_at:
            assert urgent_action.scheduled_at <= low_action.scheduled_at

    def test_empty_opportunities(self, scheduler):
        scheduled = scheduler.schedule([])
        assert scheduled == []

    def test_priority_score_formula(self, scheduler):
        high_high = make_opp("a", 0.9, "high", "low")
        low_low = make_opp("b", 0.1, "low", "high")
        scheduled = scheduler.schedule([high_high, low_low])
        assert scheduled[0].priority_score > scheduled[1].priority_score * 2

    def test_duplicate_action_types_deduped(self, scheduler):
        opps = [
            make_opp("fix_title", 0.8, "high", "low"),
            make_opp("fix_title", 0.6, "medium", "low"),
        ]
        scheduled = scheduler.schedule(opps)
        types = [s.opportunity.action_type for s in scheduled]
        assert types == ["fix_title"]

    def test_schedule_with_current_queue(self, scheduler):
        existing = [
            ScheduledAction(
                opportunity=make_opp("in_progress_action", 0.5),
                priority_score=0.5,
                scheduled_at=datetime.now(timezone.utc),
                status="in_progress",
            )
        ]
        opps = [make_opp("new_action", 0.7, "high", "low")]
        scheduled = scheduler.schedule(opps, current_queue=existing)
        assert len(scheduled) == 2
        pending = [s for s in scheduled if s.status == "pending"]
        in_progress = [s for s in scheduled if s.status == "in_progress"]
        assert len(pending) == 1
        assert len(in_progress) == 1
