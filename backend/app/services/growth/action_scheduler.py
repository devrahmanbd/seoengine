import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from app.services.growth.opportunity_detector import Opportunity

logger = logging.getLogger(__name__)


@dataclass
class ScheduledAction:
    opportunity: Opportunity
    priority_score: float
    scheduled_at: datetime | None = None
    status: Literal["pending", "scheduled", "in_progress", "completed", "failed"] = "pending"


CONFIDENCE_WEIGHT = 2.0
EFFORT_PENALTY: dict[str, float] = {"low": 1.0, "medium": 0.7, "high": 0.4}
URGENCY_BOOST = 1.5


class ActionScheduler:
    def schedule(
        self,
        opportunities: list[Opportunity],
        max_actions: int = 10,
        current_queue: list[ScheduledAction] | None = None,
    ) -> list[ScheduledAction]:
        if not opportunities:
            return []

        seen: set[str] = set()
        unique_opps: list[Opportunity] = []
        for opp in opportunities:
            if opp.action_type not in seen:
                seen.add(opp.action_type)
                unique_opps.append(opp)

        scheduled: list[ScheduledAction] = []
        now = datetime.now(timezone.utc)

        for opp in unique_opps:
            confidence_mult = (
                CONFIDENCE_WEIGHT if opp.confidence == "high" else
                (1.0 if opp.confidence == "medium" else 0.5)
            )
            effort_mult = EFFORT_PENALTY.get(opp.effort, 0.7)
            urgency = URGENCY_BOOST if opp.expected_reward > 0.7 else 1.0

            priority_score = opp.expected_reward * confidence_mult * effort_mult * urgency

            schedule_offset = max(0, int((1.0 - priority_score) * 7))
            scheduled_at = now + timedelta(hours=schedule_offset) if schedule_offset > 0 else now

            scheduled.append(ScheduledAction(
                opportunity=opp,
                priority_score=round(priority_score, 4),
                scheduled_at=scheduled_at,
                status="pending",
            ))

        if current_queue:
            in_progress_ids = {s.opportunity.action_type for s in current_queue if s.status == "in_progress"}
            for sa in scheduled:
                if sa.opportunity.action_type in in_progress_ids:
                    sa.status = "in_progress"
            scheduled.extend(s for s in current_queue if s not in scheduled)

        scheduled.sort(key=lambda s: s.priority_score, reverse=True)
        result = scheduled[:max_actions]

        logger.info("Scheduled %d actions (from %d opportunities)", len(result), len(opportunities))
        return result
