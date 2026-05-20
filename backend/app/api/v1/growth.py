import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/v1/growth", tags=["Growth"])

# These are set by main.py on startup
growth_tracker: Any = None
opportunity_detector: Any = None
action_scheduler: Any = None


@router.get("/{website_id}")
async def get_growth_state(website_id: str):
    if growth_tracker is None:
        return {"error": "Growth tracker not initialized"}
    state = await growth_tracker.get_growth_state(website_id)
    return {
        "website_id": state.website_id,
        "growth_score": state.growth_score,
        "trend": state.trend,
        "trajectory_count": state.trajectory_count,
        "avg_reward": state.avg_reward,
        "score_history": state.score_history,
        "action_effectiveness": state.action_effectiveness,
    }


@router.post("/compare")
async def compare_websites(body: dict):
    if growth_tracker is None:
        return []
    website_ids = body.get("website_ids", [])
    states = await growth_tracker.compare_websites(website_ids)
    return [
        {
            "website_id": s.website_id,
            "growth_score": s.growth_score,
            "trend": s.trend,
            "trajectory_count": s.trajectory_count,
            "avg_reward": s.avg_reward,
        }
        for s in states
    ]


@router.get("/{website_id}/intervention")
async def check_intervention(website_id: str):
    if growth_tracker is None:
        return {"needs_intervention": False}
    needs = await growth_tracker.needs_intervention(website_id)
    return {"website_id": website_id, "needs_intervention": needs}


@router.get("/{website_id}/effective-actions")
async def get_effective_actions(website_id: str, min_occurrences: int = 2):
    if growth_tracker is None:
        return {}
    return await growth_tracker.get_effective_actions(website_id, min_occurrences=min_occurrences)


@router.post("/{website_id}/opportunities")
async def get_opportunities(website_id: str, body: dict):
    if opportunity_detector is None:
        return []
    opps = await opportunity_detector.detect_opportunities(website_id, body, top_k=body.get("top_k", 5))
    return [
        {
            "action_type": o.action_type,
            "expected_reward": o.expected_reward,
            "confidence": o.confidence,
            "source": o.source,
            "effort": o.effort,
            "description": o.description,
            "evidence": o.evidence,
        }
        for o in opps
    ]


@router.post("/{website_id}/schedule")
async def schedule_actions(website_id: str, body: dict):
    if opportunity_detector is None or action_scheduler is None:
        return []
    opps = await opportunity_detector.detect_opportunities(website_id, body, top_k=body.get("top_k", 10))
    scheduled = action_scheduler.schedule(opps, max_actions=body.get("max_actions", 10))
    return [
        {
            "action_type": s.opportunity.action_type,
            "expected_reward": s.opportunity.expected_reward,
            "confidence": s.opportunity.confidence,
            "source": s.opportunity.source,
            "effort": s.opportunity.effort,
            "description": s.opportunity.description,
            "priority_score": s.priority_score,
            "scheduled_at": s.scheduled_at.isoformat() if s.scheduled_at else None,
            "status": s.status,
        }
        for s in scheduled
    ]
