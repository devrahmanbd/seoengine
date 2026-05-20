# Website Growth Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade Website Growth Engine that uses the trained PPO policy and learned patterns to automatically identify optimization opportunities, schedule actions based on expected impact, track growth trajectories, and expose everything through REST APIs and dashboard pages.

**Architecture:** 5 components — (1) GrowthTracker service for real-time monitoring & pattern detection, (2) OpportunityDetector combining PPO + cross-site patterns + site state, (3) ActionScheduler for prioritization, (4) Growth Dashboard API + frontend pages, (5) Production Decision Engine integration. Each builds on the Phase 3 learning infrastructure.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, SQLAlchemy, PyTorch, React/TypeScript, Recharts

---

## Phase 3 Review Findings

### Test Results
- **119 passed, 4 failed** across `tests/test_learning/`
- All 118 `tests/test_atropos/` tests pass (backward compatibility confirmed)

### Specific Failures

| Test | Cause | Fix |
|------|-------|-----|
| `test_collect_website_trajectories_with_tasks` | Lazy db_models import triggers `psycopg2` module lookup at test time, but `psycopg2` is not installed | Use `@pytest.mark.filterwarnings` or make `DataCollector` accept an async session factory that doesn't need engine creation at import time |
| `test_collect_all_trajectories` | Same db_models import issue | Same fix |
| `test_known_action_pattern` | Floating point: `(1.0 + 0.8 + 0.6) / 3 == 0.799999...` != `0.8` | Use `pytest.approx(0.8)` or round |
| `test_trainer_error_handled` | `TrainingPipeline.collect_and_train` doesn't catch trainer exceptions | Wrap `self._trainer.update_policy()` in try/except |

### Code Quality Issues

1. **`data_collector.py`: Lazy imports inside methods** (`from app.core.db_models import Task`, `from app.core.db_models import Website`, `from app.core.db_models import AgentLog`, `__import__("sqlalchemy")`) — these are brittle and cause import-time side effects. Move to top-level imports.

2. **`training_pipeline.py:122-123`**: The `_auto_train_loop` uses a confusing `asyncio.get_event_loop().create_future()` pattern. It should use `asyncio.sleep(interval)` with a Task cancel pattern.

3. **`feedback_loop.py`**: Accesses `pipeline._buffer` and `pipeline._transform_to_scored_data` as private attributes. Add public methods to `TrainingPipeline`.

4. **`learning/__init__.py`**: Missing exports for `DecisionIntegrator` and `GrowthScorer`.

5. **`growth_scorer.py:167`**: `trajectories[0].states[0].get("score", 0)` — `states[0]` is a dict, but `get()` on a dict is fine (no bug here, just reading confusion). Actually `trajectories[0].states` is `list[dict]`, so `.get("score")` won't work on a list — wait, `trajectories[0].states[0]` is a `dict`, so `.get()` works.

6. **No observability**: Zero logging in `growth_scorer.py`, `decision_integrator.py`, `feedback_loop.py`.

7. **`feedback_loop.py:31-35`**: `RewardCalculator.from_seo_results` signature has changed — now takes `(previous_score, current_score)` not `(dict, dict)`. The FeedbackLoop calls it with `(prev.get("score"), curr.get("score"))` which is **correct** actually since the new API takes `int|None, int|None`. But wait — the test at line 43-44 passes dicts: `({"score": prev.get("score")}, {"score": curr.get("score")})`. Let me re-check...

Actually looking more carefully:
- `feedback_loop.py:28-30`: `self._calculator.from_seo_results(prev.get("score") or 0, curr.get("score") or 0)` — this passes `int|None` values. This matches the new `RewardCalculator.from_seo_results(previous_score: int | None, current_score: int | None)` signature. Good.
- `feedback_loop.py:33-35`: `self._calculator.from_issues(len(prev.get("issues") or []), len(curr.get("issues") or []))` — this matches `from_issues(previous_count: int | None, current_count: int | None)`. Good.

But the `from_seo_results` and `from_issues` error is not triggered because these specific code paths aren't tested — the test mocks the collector.

8. **`data_collector.py:167`**: `trajectories[0].states[0].get("score", 0)` — `states` is `list[dict]`, so `states[0]` is a `dict` and `.get("score")` works. OK.

### Missing Components
- `DecisionIntegrator` and `GrowthScorer` not exported from `learning/__init__.py`
- No API endpoints exposing Phase 3 services
- No integration of Phase 3 with the main FastAPI app (`main.py` doesn't wire anything from `learning/`)
- `cross_site.py` patterns never fed back into any policy or decision

### What's Good
- RewardCalculator has a clean `Reward` dataclass with component tracking
- DecisionEngine without integrator gracefully falls back to heuristics
- All atropos tests pass cleanly
- Thread-safe ScoredDataBuffer
- Good test structure with clear fixtures
- FeedbackLoop uses `asyncio.Lock` for concurrent safety

---

## File Map

### New services
```
backend/app/services/growth/
  __init__.py
  growth_tracker.py        # Real-time growth monitoring & pattern detection
  opportunity_detector.py  # PPO + CrossSiteAnalyzer + site state combiner
  action_scheduler.py      # Priority scoring and scheduling

backend/app/api/v1/
  growth.py                # Growth Dashboard REST endpoints

backend/tests/test_growth/
  __init__.py
  test_growth_tracker.py
  test_opportunity_detector.py
  test_action_scheduler.py
  test_growth_api.py

admin/src/
  pages/GrowthPage.tsx     # Growth dashboard page
  components/
    GrowthOverview.tsx     # Growth stats cards + trend chart
    OpportunityList.tsx    # Action opportunity list
    TrajectoryChart.tsx    # Score trajectory timeline
    ActionTimeline.tsx     # Scheduled actions timeline
```

### Modified files
```
backend/main.py                          # Wire growth router
backend/app/services/learning/__init__.py # Add DecisionIntegrator, GrowthScorer exports
backend/app/services/learning/training_pipeline.py  # Fix auto_train_loop, add public buffer access
backend/app/services/learning/data_collector.py     # Fix lazy imports
backend/app/services/learning/growth_scorer.py       # Fix floating point, add logging
backend/app/services/learning/decision_integrator.py # Add logging
backend/app/services/learning/feedback_loop.py       # Use public pipeline methods
admin/src/App.tsx                       # Add Growth route
admin/src/components/Layout.tsx         # Add Growth nav item
admin/src/lib/api.ts                    # Add growth API client
admin/src/types/index.ts                # Add growth types
```

---

## Key Shared Interfaces

```python
# growth_tracker.py
@dataclass
class GrowthState:
    website_id: str
    current_score: float
    score_history: list[float]
    trajectory_count: int
    avg_reward: float
    trend: Literal["accelerating", "decelerating", "plateauing", "declining", "unknown"]
    action_effectiveness: dict[str, float]

# opportunity_detector.py
@dataclass
class Opportunity:
    action_type: str
    expected_reward: float
    confidence: Literal["high", "medium", "low"]
    source: Literal["policy", "cross_site", "heuristic"]
    effort: Literal["low", "medium", "high"]
    description: str
    evidence: list[str]

# action_scheduler.py
@dataclass
class ScheduledAction:
    opportunity: Opportunity
    priority_score: float
    scheduled_at: datetime | None
    status: Literal["pending", "scheduled", "in_progress", "completed", "failed"]
```

---

### Task 1: Fix Phase 3 bugs and improve code quality

**Files:**
- Modify: `backend/app/services/learning/__init__.py`
- Modify: `backend/app/services/learning/data_collector.py`
- Modify: `backend/app/services/learning/growth_scorer.py`
- Modify: `backend/app/services/learning/training_pipeline.py`
- Modify: `backend/app/services/learning/decision_integrator.py`
- Modify: `backend/app/services/learning/feedback_loop.py`

- [ ] **Step 1: Fix `learning/__init__.py` exports**

Replace content:
```python
from app.services.atropos.trainer import PPOTrainer
from app.services.learning.data_collector import DataCollector
from app.services.learning.decision_integrator import DecisionIntegrator
from app.services.learning.feedback_loop import FeedbackLoop
from app.services.learning.growth_scorer import GrowthScorer
from app.services.learning.reward_calculator import RewardCalculator
from app.services.learning.training_pipeline import TrainingPipeline

__all__ = [
    "DataCollector",
    "DecisionIntegrator",
    "FeedbackLoop",
    "GrowthScorer",
    "PPOTrainer",
    "RewardCalculator",
    "TrainingPipeline",
]
```

- [ ] **Step 2: Fix `data_collector.py` lazy imports**

Move all lazy `from app.core.db_models import ...` and `__import__("sqlalchemy")` calls to top-level imports:

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from app.core.db_models import SEOResult, Task, AgentLog, Website
```

Delete the `from app.core.db_models import Task` on line 52, the `from app.core.db_models import Website` on line 106, and the `from app.core.db_models import AgentLog` on line 120. Replace `__import__("sqlalchemy").select(...)` on lines 24, 58, 108, 123 with `select(...)`.

- [ ] **Step 3: Fix `growth_scorer.py` test precision issue**

In `predict_growth`, round the predicted value:
```python
predicted = round(sum(similar) / len(similar), 4)
```

- [ ] **Step 4: Fix `training_pipeline.py` — catch trainer exceptions**

Wrap `await self._trainer.update_policy(trajectories)` in try/except:
```python
training_stats: dict = {}
if self._trainer is not None:
    try:
        training_stats = await self._trainer.update_policy(trajectories)
    except Exception as e:
        training_stats = {"error": str(e)}
self._stats["total_training_runs"] += 1
self._stats["last_training_stats"] = training_stats
```

- [ ] **Step 5: Fix `training_pipeline.py` — `_auto_train_loop` sleep pattern**

Replace the confusing future-creation pattern:
```python
async def _auto_train_loop(self, interval: int) -> None:
    while not self._stop_event.is_set():
        await self.collect_from_all_sites()
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
```

- [ ] **Step 6: Fix `training_pipeline.py` — add public buffer access methods**

```python
def add_to_buffer(self, scored_data: list) -> None:
    self._buffer.extend(scored_data)

@property
def buffer_size(self) -> int:
    return len(self._buffer)
```

- [ ] **Step 7: Add logging to `decision_integrator.py`**

```python
import logging
logger = logging.getLogger(__name__)

# Add to recommend_actions:
logger.info("Recommending top-%d actions for state (has_trained=%s)", top_k, self.has_trained_policy())

# Add to enrich_decision:
logger.info("Enriched decision for state (confidence=%s, impact=%.4f)", enriched["data_confidence"], enriched["expected_impact"])
```

- [ ] **Step 8: Add logging to `growth_scorer.py`**

```python
import logging
logger = logging.getLogger(__name__)

# Add to score_growth:
logger.info("Growth score for %s: %.4f (trend=%s, trajs=%d)", website_id, growth_score, trend, len(trajectories))

# Add to predict_growth:
logger.info("Predicted growth for %s/%s: %.4f (confidence=%s, samples=%d)", website_id, action_type, predicted, confidence, len(similar))
```

- [ ] **Step 9: Fix `feedback_loop.py` to use public pipeline methods**

Replace `self._pipeline._buffer.extend(scored)` with `self._pipeline.add_to_buffer(scored)`:
```python
if self._pipeline is not None:
    scored = self._pipeline._transform_to_scored_data([trajectory])
    self._pipeline.add_to_buffer(scored)
```

- [ ] **Step 10: Run tests to confirm fixes**

Run: `cd backend && python3 -m pytest tests/test_learning/ -v`
Expected: 123 passed, 0 failed

- [ ] **Step 11: Commit**

```bash
git add backend/app/services/learning/
git commit -m "fix: Phase 3 code quality and test failures"
```

---

### Task 2: Create Growth Tracker Service

**Files:**
- Create: `backend/app/services/growth/__init__.py`
- Create: `backend/app/services/growth/growth_tracker.py`
- Test: `backend/tests/test_growth/test_growth_tracker.py`

- [ ] **Step 1: Create `backend/app/services/growth/__init__.py`**

```python
from .growth_tracker import GrowthTracker, GrowthState
from .opportunity_detector import OpportunityDetector, Opportunity
from .action_scheduler import ActionScheduler, ScheduledAction

__all__ = [
    "GrowthTracker",
    "GrowthState",
    "OpportunityDetector",
    "Opportunity",
    "ActionScheduler",
    "ScheduledAction",
]
```

- [ ] **Step 2: Write the failing tests**

Create `backend/tests/test_growth/__init__.py` (empty file) and `backend/tests/test_growth/test_growth_tracker.py`:

```python
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from app.services.growth.growth_tracker import GrowthTracker


@pytest.fixture
def mock_growth_scorer():
    gs = MagicMock()
    gs.score_growth = AsyncMock(return_value={
        "website_id": "site-1", "growth_score": 0.65, "trend": "accelerating",
        "trajectories_count": 5, "avg_reward": 0.65,
    })
    gs.get_action_effectiveness = AsyncMock(return_value={
        "fix_title": {"count": 3, "total_reward": 2.4, "avg_reward": 0.8},
        "optimize_content": {"count": 2, "total_reward": 1.0, "avg_reward": 0.5},
    })
    gs.predict_growth = AsyncMock(return_value={
        "website_id": "site-1", "predicted_growth": 0.75,
        "confidence": "high", "similar_actions_found": 5, "action_type": "fix_title",
    })
    return gs


@pytest.fixture
def mock_data_collector():
    dc = MagicMock()
    dc.get_website_growth_metrics = AsyncMock(return_value={
        "website_id": "site-1", "total_trajectories": 5,
        "avg_reward": 0.65, "score_trend": "improving", "total_actions": 8,
    })
    return dc


@pytest.fixture
def tracker(mock_growth_scorer, mock_data_collector):
    return GrowthTracker(
        growth_scorer=mock_growth_scorer,
        data_collector=mock_data_collector,
    )


class TestGrowthTracker:
    @pytest.mark.asyncio
    async def test_get_growth_state(self, tracker):
        state = await tracker.get_growth_state("site-1")
        assert state.website_id == "site-1"
        assert state.growth_score == 0.65
        assert state.trend == "accelerating"
        assert state.trajectory_count == 5
        assert isinstance(state.score_history, list)

    @pytest.mark.asyncio
    async def test_get_growth_state_detects_plateau(self, tracker, mock_growth_scorer):
        mock_growth_scorer.score_growth.return_value["trend"] = "stable"
        state = await tracker.get_growth_state("site-1")
        assert state.trend == "plateauing"

    @pytest.mark.asyncio
    async def test_get_growth_state_declining(self, tracker, mock_growth_scorer):
        mock_growth_scorer.score_growth.return_value["trend"] = "declining"
        state = await tracker.get_growth_state("site-1")
        assert state.trend == "declining"

    @pytest.mark.asyncio
    async def test_get_growth_state_no_data(self, tracker, mock_growth_scorer):
        mock_growth_scorer.score_growth.return_value = {
            "website_id": "site-1", "growth_score": 0.0,
            "trend": "unknown", "trajectories_count": 0, "avg_reward": 0.0,
        }
        state = await tracker.get_growth_state("site-1")
        assert state.trend == "unknown"
        assert state.trajectory_count == 0

    @pytest.mark.asyncio
    async def test_get_growth_state_no_collector(self):
        tracker = GrowthTracker(growth_scorer=MagicMock())
        state = await tracker.get_growth_state("site-1")
        assert state.score_history == []

    @pytest.mark.asyncio
    async def test_compare_websites(self, tracker):
        mock_gs = tracker._growth_scorer
        mock_gs.score_growth = AsyncMock(side_effect=[
            {"website_id": "site-1", "growth_score": 0.8, "trend": "accelerating", "trajectories_count": 5, "avg_reward": 0.8},
            {"website_id": "site-2", "growth_score": 0.3, "trend": "declining", "trajectories_count": 3, "avg_reward": 0.3},
        ])
        results = await tracker.compare_websites(["site-1", "site-2"])
        assert len(results) == 2
        assert results[0].website_id == "site-1"
        assert results[0].growth_score > results[1].growth_score

    @pytest.mark.asyncio
    async def test_needs_intervention_accelerating(self, tracker):
        needs = await tracker.needs_intervention("site-1")
        assert needs is False

    @pytest.mark.asyncio
    async def test_needs_intervention_declining(self, tracker, mock_growth_scorer):
        mock_growth_scorer.score_growth.return_value["trend"] = "declining"
        mock_growth_scorer.score_growth.return_value["growth_score"] = -0.3
        needs = await tracker.needs_intervention("site-1")
        assert needs is True

    @pytest.mark.asyncio
    async def test_needs_intervention_plateau(self, tracker, mock_growth_scorer):
        mock_growth_scorer.score_growth.return_value["trend"] = "stable"
        mock_growth_scorer.score_growth.return_value["growth_score"] = 0.15
        needs = await tracker.needs_intervention("site-1")
        assert needs is True

    @pytest.mark.asyncio
    async def test_get_effective_actions(self, tracker):
        actions = await tracker.get_effective_actions("site-1", min_occurrences=2)
        assert "fix_title" in actions
        assert "optimize_content" in actions
        assert actions["fix_title"]["avg_reward"] == 0.8

    @pytest.mark.asyncio
    async def test_get_effective_actions_filters_by_count(self, tracker):
        actions = await tracker.get_effective_actions("site-1", min_occurrences=3)
        assert "fix_title" in actions
        assert "optimize_content" not in actions
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_growth/test_growth_tracker.py -v`
Expected: ModuleNotFoundError for `app.services.growth.growth_tracker`

- [ ] **Step 4: Create `backend/app/services/growth/growth_tracker.py`**

```python
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)


@dataclass
class GrowthState:
    website_id: str
    growth_score: float
    trend: Literal["accelerating", "decelerating", "plateauing", "declining", "unknown"]
    trajectory_count: int
    avg_reward: float
    score_history: list[float] = field(default_factory=list)
    action_effectiveness: dict[str, dict] = field(default_factory=dict)


INTERVENTION_THRESHOLD = 0.2


class GrowthTracker:
    def __init__(self, growth_scorer: Any = None, data_collector: Any = None):
        self._growth_scorer = growth_scorer
        self._data_collector = data_collector

    async def get_growth_state(self, website_id: str) -> GrowthState:
        if self._growth_scorer is None:
            return GrowthState(
                website_id=website_id, growth_score=0.0,
                trend="unknown", trajectory_count=0, avg_reward=0.0,
            )

        score_data = await self._growth_scorer.score_growth(website_id)

        trend: Literal["accelerating", "decelerating", "plateauing", "declining", "unknown"]
        raw_trend = score_data.get("trend", "unknown")
        if raw_trend == "stable":
            trend = "plateauing"
        elif raw_trend in ("accelerating", "declining", "unknown"):
            trend = raw_trend
        else:
            trend = "unknown"

        score_history: list[float] = []
        if self._data_collector is not None:
            metrics = await self._data_collector.get_website_growth_metrics(website_id)
            score_history = metrics.get("score_progression", [])

        action_effectiveness: dict[str, dict] = {}
        if self._growth_scorer is not None:
            ae = await self._growth_scorer.get_action_effectiveness(website_id)
            for k, v in ae.items():
                action_effectiveness[k] = {
                    "count": v.get("count", 0),
                    "avg_reward": v.get("avg_reward", 0.0),
                }

        return GrowthState(
            website_id=website_id,
            growth_score=score_data.get("growth_score", 0.0),
            trend=trend,
            trajectory_count=score_data.get("trajectories_count", 0),
            avg_reward=score_data.get("avg_reward", 0.0),
            score_history=score_history,
            action_effectiveness=action_effectiveness,
        )

    async def compare_websites(self, website_ids: list[str]) -> list[GrowthState]:
        states: list[GrowthState] = []
        for wid in website_ids:
            state = await self.get_growth_state(wid)
            states.append(state)
        states.sort(key=lambda s: s.growth_score, reverse=True)
        return states

    async def needs_intervention(self, website_id: str) -> bool:
        state = await self.get_growth_state(website_id)
        if state.trend == "declining":
            return True
        if state.trend == "plateauing" and state.growth_score < INTERVENTION_THRESHOLD:
            return True
        return False

    async def get_effective_actions(
        self, website_id: str, min_occurrences: int = 2
    ) -> dict[str, dict]:
        if self._growth_scorer is None:
            return {}
        eff = await self._growth_scorer.get_action_effectiveness(website_id)
        return {
            k: v for k, v in eff.items()
            if v.get("count", 0) >= min_occurrences
        }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_growth/test_growth_tracker.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/growth/ backend/tests/test_growth/
git commit -m "feat: add GrowthTracker service for real-time growth monitoring"
```

---

### Task 3: Create Opportunity Detector

**Files:**
- Create: `backend/app/services/growth/opportunity_detector.py`
- Test: `backend/tests/test_growth/test_opportunity_detector.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.growth.opportunity_detector import OpportunityDetector, Opportunity


@pytest.fixture
def mock_decision_integrator():
    di = MagicMock()
    di.recommend_actions = AsyncMock(return_value=[
        {"action_type": "fix_title", "confidence": 0.85, "reason": "policy_recommended"},
        {"action_type": "add_schema", "confidence": 0.72, "reason": "policy_recommended"},
    ])
    di.score_action = AsyncMock(side_effect=lambda s, a: {
        "fix_title": 0.85, "add_schema": 0.72, "optimize_content": 0.45,
    }.get(a.get("action_type"), 0.5))
    return di


@pytest.fixture
def mock_cross_site():
    cs = MagicMock()
    cs.get_insights_for_site = AsyncMock(return_value=[
        MagicMock(pattern_id="p1", name="fix_title_pattern", description="Fixing titles helps", avg_improvement=0.3, site_count=5, action_sequence=["fix_title"]),
    ])
    return cs


@pytest.fixture
def detector(mock_decision_integrator, mock_cross_site):
    return OpportunityDetector(
        decision_integrator=mock_decision_integrator,
        cross_site_analyzer=mock_cross_site,
    )


class TestOpportunityDetector:
    @pytest.mark.asyncio
    async def test_detect_opportunities(self, detector):
        state = {"score": 55, "issues": 5, "features": [0.5] * 128}
        opps = await detector.detect_opportunities("site-1", state)
        assert len(opps) > 0
        assert all(isinstance(o, Opportunity) for o in opps)

    @pytest.mark.asyncio
    async def test_opportunity_has_required_fields(self, detector):
        state = {"score": 55, "issues": 5}
        opps = await detector.detect_opportunities("site-1", state)
        for opp in opps:
            assert opp.action_type
            assert isinstance(opp.expected_reward, float)
            assert opp.confidence in ("high", "medium", "low")
            assert opp.source in ("policy", "cross_site", "heuristic")
            assert opp.effort in ("low", "medium", "high")

    @pytest.mark.asyncio
    async def test_high_confidence_policy_actions_sorted_first(self, detector):
        state = {"score": 30, "issues": 10}
        opps = await detector.detect_opportunities("site-1", state)
        confidences = [o.expected_reward for o in opps]
        assert confidences == sorted(confidences, reverse=True)

    @pytest.mark.asyncio
    async def test_low_score_adds_heuristic_actions(self, detector):
        state = {"score": 25, "issues": 12}
        opps = await detector.detect_opportunities("site-1", state)
        sources = [o.source for o in opps]
        assert "heuristic" in sources

    @pytest.mark.asyncio
    async def test_no_integrator_falls_back(self, mock_cross_site):
        detector = OpportunityDetector(cross_site_analyzer=mock_cross_site)
        state = {"score": 50, "issues": 5}
        opps = await detector.detect_opportunities("site-1", state)
        assert len(opps) >= 2
        assert all(o.source == "heuristic" for o in opps)

    @pytest.mark.asyncio
    async def test_cross_site_patterns_appear(self, detector):
        state = {"score": 70, "issues": 3}
        opps = await detector.detect_opportunities("site-1", state)
        sources = [o.source for o in opps]
        assert "cross_site" in sources or "policy" in sources

    @pytest.mark.asyncio
    async def test_predict_growth_called(self, detector, mock_decision_integrator):
        state = {"score": 50, "issues": 5}
        _ = await detector.detect_opportunities("site-1", state)
        mock_decision_integrator.recommend_actions.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_growth/test_opportunity_detector.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Create `backend/app/services/growth/opportunity_detector.py`**

```python
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)


@dataclass
class Opportunity:
    action_type: str
    expected_reward: float
    confidence: Literal["high", "medium", "low"]
    source: Literal["policy", "cross_site", "heuristic"]
    effort: Literal["low", "medium", "high"]
    description: str
    evidence: list[str] = field(default_factory=list)


EFFORT_MAP: dict[str, Literal["low", "medium", "high"]] = {
    "fix_title": "low",
    "fix_meta": "low",
    "fix_images": "low",
    "optimize_content": "medium",
    "improve_cwv": "medium",
    "add_schema": "medium",
    "build_backlinks": "high",
    "fix_headings": "low",
    "run_technical_audit": "low",
    "run_full_audit": "medium",
}


class OpportunityDetector:
    def __init__(
        self,
        decision_integrator: Any = None,
        cross_site_analyzer: Any = None,
    ):
        self._integrator = decision_integrator
        self._cross_site = cross_site_analyzer

    async def detect_opportunities(
        self, website_id: str, state: dict, top_k: int = 5
    ) -> list[Opportunity]:
        opportunities: list[Opportunity] = []

        if self._integrator is not None:
            policy_recs = await self._integrator.recommend_actions(state, top_k=top_k)
            for rec in policy_recs:
                reward = rec.get("confidence", 0.5)
                opportunities.append(Opportunity(
                    action_type=rec.get("action_type", "unknown"),
                    expected_reward=reward,
                    confidence="high" if reward > 0.7 else ("medium" if reward > 0.4 else "low"),
                    source="policy",
                    effort=EFFORT_MAP.get(rec.get("action_type", ""), "medium"),
                    description=f"Policy recommends: {rec.get('reason', 'policy_recommended')}",
                    evidence=[f"Policy confidence: {reward:.2f}"],
                ))

        if self._cross_site is not None:
            try:
                patterns = await self._cross_site.get_insights_for_site(website_id)
                for pattern in patterns[:3]:
                    for action in pattern.action_sequence:
                        opportunities.append(Opportunity(
                            action_type=action,
                            expected_reward=pattern.avg_improvement,
                            confidence="medium" if pattern.site_count > 3 else "low",
                            source="cross_site",
                            effort=EFFORT_MAP.get(action, "medium"),
                            description=pattern.description[:120],
                            evidence=[
                                f"Pattern: {pattern.name}",
                                f"Sites: {pattern.site_count}",
                                f"Avg improvement: {pattern.avg_improvement:.2f}",
                            ],
                        ))
            except Exception as e:
                logger.warning("Cross-site analysis failed for %s: %s", website_id, e)

        score = state.get("score", 50)
        issues = state.get("issues", 0)
        if score < 40:
            opportunities.append(Opportunity(
                action_type="run_full_audit",
                expected_reward=0.3,
                confidence="medium",
                source="heuristic",
                effort="medium",
                description=f"Low score ({score}) triggers full audit",
                evidence=[f"Score {score} below 40 threshold"],
            ))
        if issues > 5:
            opportunities.append(Opportunity(
                action_type="fix_meta_tags",
                expected_reward=0.25,
                confidence="medium",
                source="heuristic",
                effort="low",
                description=f"High issue count ({issues}) suggests meta fixes",
                evidence=[f"{issues} issues detected"],
            ))

        opportunities.sort(key=lambda o: o.expected_reward, reverse=True)
        logger.info("Detected %d opportunities for site %s", len(opportunities), website_id)
        return opportunities[:top_k]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_growth/test_opportunity_detector.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/growth/opportunity_detector.py backend/tests/test_growth/test_opportunity_detector.py
git commit -m "feat: add OpportunityDetector combining PPO + cross-site + heuristics"
```

---

### Task 4: Create Action Scheduler

**Files:**
- Create: `backend/app/services/growth/action_scheduler.py`
- Test: `backend/tests/test_growth/test_action_scheduler.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_growth/test_action_scheduler.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Create `backend/app/services/growth/action_scheduler.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_growth/test_action_scheduler.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/growth/action_scheduler.py backend/tests/test_growth/test_action_scheduler.py
git commit -m "feat: add ActionScheduler for prioritization and scheduling"
```

---

### Task 5: Create Growth Dashboard API

**Files:**
- Create: `backend/app/api/v1/growth.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_growth/test_growth_api.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.api.v1.growth import router as growth_router
from app.services.growth.growth_tracker import GrowthState


@pytest.fixture
def app():
    a = FastAPI()
    a.include_router(growth_router, prefix="/api/admin/v1/growth")
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
        mock_sched = MagicMock()
        mock_sched.schedule = MagicMock(return_value=[
            MagicMock(
                opportunity=MagicMock(
                    action_type="fix_title", expected_reward=0.85, confidence="high",
                    source="policy", effort="low", description="Fix the title",
                    evidence=[],
                ),
                priority_score=1.7, scheduled_at="2026-05-21T00:00:00Z", status="pending",
            ),
        ])
        with patch("app.api.v1.growth.action_scheduler", mock_sched):
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_growth/test_growth_api.py -v`
Expected: ModuleNotFoundError for `app.api.v1.growth`

- [ ] **Step 3: Create `backend/app/api/v1/growth.py`**

```python
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
```

- [ ] **Step 4: Wire the router in `main.py`**

Add import:
```python
from app.api.v1.growth import router as growth_router
from app.services.growth.growth_tracker import GrowthTracker
from app.services.growth.opportunity_detector import OpportunityDetector
from app.services.growth.action_scheduler import ActionScheduler
```

Add after other routers:
```python
app.include_router(growth_router, tags=["Growth"])
```

Add to lifespan:
```python
# Initialize growth engine
from app.services.growth import growth_tracker as gt_mod
from app.services.learning import GrowthScorer, DataCollector, DecisionIntegrator
from app.services.semantic.cross_site import CrossSiteAnalyzer
from app.services.semantic.db import SemanticDB

db = SemanticDB()
cross_site = CrossSiteAnalyzer(db)
collector = DataCollector()
scorer = GrowthScorer(collector=collector)
integrator = DecisionIntegrator()
gt_tracker = GrowthTracker(growth_scorer=scorer, data_collector=collector)
gt_mod.growth_tracker = gt_tracker
gt_mod.opportunity_detector = OpportunityDetector(
    decision_integrator=integrator,
    cross_site_analyzer=cross_site,
)
gt_mod.action_scheduler = ActionScheduler()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_growth/test_growth_api.py -v`
Expected: All pass

- [ ] **Step 6: Run all tests to verify backward compatibility**

Run: `cd backend && python3 -m pytest tests/test_atropos/ tests/test_learning/ tests/test_growth/ -v`
Expected: All 130+ tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/growth.py backend/main.py backend/tests/test_growth/test_growth_api.py
git commit -m "feat: add Growth Dashboard API endpoints"
```

---

### Task 6: Build Production Decision Engine Integration

**Files:**
- Modify: `backend/app/core/agents/decision_engine.py`
- Modify: `backend/app/services/learning/decision_integrator.py`
- Test: Existing `test_decision_engine_integration.py` already has good coverage

- [ ] **Step 1: Enhance `DecisionIntegrator` with logging and metrics**

```python
import logging
from typing import Any

from app.services.atropos.scored_data_api import ScoredDataBuffer

logger = logging.getLogger(__name__)


class DecisionIntegrator:
    def __init__(self, trainer: Any = None, buffer: ScoredDataBuffer | None = None):
        self._trainer = trainer
        self._buffer = buffer
        self._action_history: list[dict] = []
        self._total_decisions = 0
        self._total_policy_hits = 0

    async def recommend_actions(self, state: dict, top_k: int = 3) -> list[dict]:
        logger.info("Recommending top-%d actions for state (has_trained=%s)", top_k, self.has_trained_policy())
        if not self.has_trained_policy():
            return [
                {"action_type": "run_technical_audit", "confidence": 0.5, "reason": "default"},
                {"action_type": "optimize_content", "confidence": 0.5, "reason": "default"},
            ]

        recommendations: list[dict] = []
        action_types = ["run_technical_audit", "optimize_content", "fix_meta_tags", "improve_cwv", "add_schema", "build_backlinks"]
        for at in action_types:
            score = await self.score_action(state, {"action_type": at})
            recommendations.append({
                "action_type": at,
                "confidence": float(score),
                "reason": "policy_recommended" if score > 0.5 else "policy_discouraged",
            })

        recommendations.sort(key=lambda x: x["confidence"], reverse=True)
        return recommendations[:top_k]

    async def score_action(self, state: dict, action: dict) -> float:
        if self._trainer is None:
            return 0.5
        try:
            tensor = self._trainer._state_to_tensor(state)
            action_idx = self._trainer._get_action_idx(action)
            import torch
            with torch.no_grad():
                dist = self._trainer._policy(tensor.unsqueeze(0))
                prob = dist.probs[0, action_idx].item()
            return float(prob)
        except Exception as e:
            logger.warning("Failed to score action: %s", e)
            return 0.5

    async def get_action_value(self, state: dict, action: dict) -> float:
        if self._trainer is None:
            return 0.0
        try:
            tensor = self._trainer._state_to_tensor(state)
            import torch
            with torch.no_grad():
                value = self._trainer._value(tensor.unsqueeze(0))
            return float(value.item())
        except Exception:
            return 0.0

    def has_trained_policy(self) -> bool:
        if self._trainer is None:
            return False
        return self._trainer._train_step > 0

    async def enrich_decision(self, state: dict, llm_decision: dict) -> dict:
        self._total_decisions += 1

        if not self.has_trained_policy():
            enriched = dict(llm_decision)
            enriched["policy_recommendations"] = []
            enriched["data_confidence"] = "low"
            enriched["expected_impact"] = 0.0
            return enriched

        recommendations = await self.recommend_actions(state, top_k=3)
        best_action = recommendations[0] if recommendations else {}
        expected_impact = await self.get_action_value(state, best_action) if best_action else 0.0

        if expected_impact > 0:
            self._total_policy_hits += 1

        enriched = dict(llm_decision)
        enriched["policy_recommendations"] = recommendations
        enriched["data_confidence"] = "medium" if expected_impact > 0 else "low"
        enriched["expected_impact"] = expected_impact

        self._action_history.append({
            "state": state,
            "llm_decision": llm_decision,
            "policy_recommendations": recommendations,
            "expected_impact": expected_impact,
        })

        logger.info("Enriched decision #%d (confidence=%s, impact=%.4f)", self._total_decisions, enriched["data_confidence"], expected_impact)
        return enriched

    def get_stats(self) -> dict:
        return {
            "total_decisions": self._total_decisions,
            "total_policy_hits": self._total_policy_hits,
            "history_size": len(self._action_history),
            "has_trained_policy": self.has_trained_policy(),
        }
```

- [ ] **Step 5: Update the decision integrator test**

Update `tests/test_learning/test_decision_integrator.py`:
```python
# Add to TestHasTrainedPolicy:
class TestStats:
    def test_get_stats(self, integrator, integrator_no_trainer):
        stats = integrator.get_stats()
        assert stats["total_decisions"] == 0
        assert stats["has_trained_policy"] is True

        stats2 = integrator_no_trainer.get_stats()
        assert stats2["has_trained_policy"] is False
```

- [ ] **Step 6: Run tests**

Run: `cd backend && python3 -m pytest tests/test_learning/test_decision_integrator.py tests/test_learning/test_decision_engine_integration.py -v`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/learning/decision_integrator.py backend/tests/test_learning/test_decision_integrator.py
git commit -m "feat: enhance DecisionIntegrator with logging, metrics, and stats"
```

---

### Task 7: Build Growth Dashboard Frontend

**Files:**
- Modify: `admin/src/App.tsx`
- Modify: `admin/src/components/Layout.tsx`
- Modify: `admin/src/lib/api.ts`
- Modify: `admin/src/types/index.ts`
- Create: `admin/src/pages/GrowthPage.tsx`
- Create: `admin/src/components/GrowthOverview.tsx`
- Create: `admin/src/components/OpportunityList.tsx`
- Create: `admin/src/components/TrajectoryChart.tsx`
- Create: `admin/src/components/ActionTimeline.tsx`

- [ ] **Step 1: Add types to `admin/src/types/index.ts`**

```typescript
export interface GrowthState {
  website_id: string;
  growth_score: number;
  trend: 'accelerating' | 'decelerating' | 'plateauing' | 'declining' | 'unknown';
  trajectory_count: number;
  avg_reward: number;
  score_history: number[];
  action_effectiveness: Record<string, { count: number; avg_reward: number }>;
}

export interface Opportunity {
  action_type: string;
  expected_reward: number;
  confidence: 'high' | 'medium' | 'low';
  source: 'policy' | 'cross_site' | 'heuristic';
  effort: 'low' | 'medium' | 'high';
  description: string;
  evidence: string[];
}

export interface ScheduledAction {
  action_type: string;
  expected_reward: number;
  confidence: string;
  source: string;
  effort: string;
  description: string;
  priority_score: number;
  scheduled_at: string | null;
  status: 'pending' | 'scheduled' | 'in_progress' | 'completed' | 'failed';
}
```

- [ ] **Step 2: Add API client methods to `admin/src/lib/api.ts`**

```typescript
export const growthApi = {
  getState: (websiteId: string) => api.get(`/growth/${websiteId}`),
  compare: (websiteIds: string[]) => api.post('/growth/compare', { website_ids: websiteIds }),
  checkIntervention: (websiteId: string) => api.get(`/growth/${websiteId}/intervention`),
  effectiveActions: (websiteId: string) => api.get(`/growth/${websiteId}/effective-actions`),
  opportunities: (websiteId: string, data: any) => api.post(`/growth/${websiteId}/opportunities`, data),
  schedule: (websiteId: string, data: any) => api.post(`/growth/${websiteId}/schedule`, data),
}
```

- [ ] **Step 3: Add Growth nav item in `admin/src/components/Layout.tsx`**

Add to navItems:
```typescript
import { TrendingUp } from 'lucide-react'

const navItems = [
  ...
  { path: '/growth', icon: TrendingUp, label: 'Growth' },
]
```

- [ ] **Step 4: Add route in `admin/src/App.tsx`**

```typescript
import GrowthPage from './pages/GrowthPage'

// Add inside ProtectedRoute Layout:
<Route path="growth" element={<GrowthPage />} />
```

- [ ] **Step 5: Create `admin/src/components/GrowthOverview.tsx`**

```tsx
import { GrowthState } from '../types'

interface Props {
  state: GrowthState | null
  loading: boolean
}

function TrendBadge({ trend }: { trend: string }) {
  const colors: Record<string, string> = {
    accelerating: 'bg-emerald-100 text-emerald-800',
    decelerating: 'bg-amber-100 text-amber-800',
    plateauing: 'bg-blue-100 text-blue-800',
    declining: 'bg-rose-100 text-rose-800',
    unknown: 'bg-slate-100 text-slate-600',
  }
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors[trend] || colors.unknown}`}>
      {trend}
    </span>
  )
}

export default function GrowthOverview({ state, loading }: Props) {
  if (loading) {
    return <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {[1,2,3,4].map(i => (
        <div key={i} className="h-24 bg-slate-100 rounded-lg animate-pulse" />
      ))}
    </div>
  }

  if (!state) {
    return <div className="text-center py-12 text-slate-500">Select a website to view growth data</div>
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <div className="text-sm text-slate-500 mb-1">Growth Score</div>
        <div className="text-2xl font-bold text-slate-900">
          {Math.round(state.growth_score * 100)}%
        </div>
      </div>
      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <div className="text-sm text-slate-500 mb-1">Trend</div>
        <TrendBadge trend={state.trend} />
      </div>
      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <div className="text-sm text-slate-500 mb-1">Trajectories</div>
        <div className="text-2xl font-bold text-slate-900">{state.trajectory_count}</div>
      </div>
      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <div className="text-sm text-slate-500 mb-1">Avg Reward</div>
        <div className="text-2xl font-bold text-slate-900">{state.avg_reward.toFixed(2)}</div>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Create `admin/src/components/TrajectoryChart.tsx`**

```tsx
interface Props {
  scoreHistory: number[]
  loading: boolean
}

export default function TrajectoryChart({ scoreHistory, loading }: Props) {
  if (loading) {
    return <div className="h-64 bg-slate-100 rounded-lg animate-pulse" />
  }

  if (!scoreHistory.length) {
    return <div className="h-64 bg-white rounded-lg border border-slate-200 flex items-center justify-center text-slate-500">
      No trajectory data available
    </div>
  }

  const maxScore = Math.max(...scoreHistory, 100)
  const minScore = Math.min(...scoreHistory, 0)
  const range = maxScore - minScore || 1
  const width = 100
  const height = 200
  const points = scoreHistory.map((s, i) => {
    const x = (i / Math.max(scoreHistory.length - 1, 1)) * width
    const y = height - ((s - minScore) / range) * height
    return `${x},${y}`
  }).join(' ')

  const gradient = scoreHistory[0] <= scoreHistory[scoreHistory.length - 1]
    ? '#10B981' : '#F43F5E'

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <h3 className="text-sm font-medium text-slate-700 mb-4">Score Trajectory</h3>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-48">
        <polyline
          fill="none"
          stroke={gradient}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points}
        />
      </svg>
      <div className="flex justify-between text-xs text-slate-400 mt-2">
        <span>{scoreHistory.length} data points</span>
        <span>{minScore} - {maxScore}</span>
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Create `admin/src/components/OpportunityList.tsx`**

```tsx
import { Opportunity } from '../types'

interface Props {
  opportunities: Opportunity[]
  loading: boolean
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const colors: Record<string, string> = {
    high: 'bg-emerald-100 text-emerald-700',
    medium: 'bg-amber-100 text-amber-700',
    low: 'bg-slate-100 text-slate-600',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[confidence] || colors.low}`}>
      {confidence}
    </span>
  )
}

function EffortBadge({ effort }: { effort: string }) {
  const colors: Record<string, string> = {
    low: 'bg-green-100 text-green-700',
    medium: 'bg-amber-100 text-amber-700',
    high: 'bg-rose-100 text-rose-700',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[effort] || colors.medium}`}>
      {effort}
    </span>
  )
}

export default function OpportunityList({ opportunities, loading }: Props) {
  if (loading) {
    return <div className="space-y-3">
      {[1,2,3].map(i => <div key={i} className="h-16 bg-slate-100 rounded-lg animate-pulse" />)}
    </div>
  }

  if (!opportunities.length) {
    return <div className="text-center py-8 text-slate-500">No opportunities found</div>
  }

  return (
    <div className="space-y-2">
      {opportunities.map((opp, i) => (
        <div key={i} className="bg-white rounded-lg border border-slate-200 p-4 hover:border-primary/30 transition-colors">
          <div className="flex items-start justify-between mb-2">
            <div>
              <span className="font-medium text-slate-900 text-sm">{opp.action_type}</span>
              <span className="ml-2 text-xs text-slate-400">via {opp.source}</span>
            </div>
            <div className="flex gap-2">
              <ConfidenceBadge confidence={opp.confidence} />
              <EffortBadge effort={opp.effort} />
            </div>
          </div>
          <p className="text-sm text-slate-600 mb-2">{opp.description}</p>
          <div className="flex items-center gap-4 text-xs text-slate-400">
            <span>Expected reward: {(opp.expected_reward * 100).toFixed(0)}%</span>
            {opp.evidence.length > 0 && (
              <span title={opp.evidence.join('\n')} className="cursor-help underline decoration-dotted">
                {opp.evidence.length} evidence(s)
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 8: Create `admin/src/components/ActionTimeline.tsx`**

```tsx
import { ScheduledAction } from '../types'

interface Props {
  actions: ScheduledAction[]
  loading: boolean
}

export default function ActionTimeline({ actions, loading }: Props) {
  if (loading) {
    return <div className="space-y-3">
      {[1,2,3].map(i => <div key={i} className="h-12 bg-slate-100 rounded-lg animate-pulse" />)}
    </div>
  }

  if (!actions.length) {
    return <div className="text-center py-8 text-slate-500">No scheduled actions</div>
  }

  const statusColors: Record<string, string> = {
    pending: 'bg-slate-400',
    scheduled: 'bg-blue-400',
    in_progress: 'bg-amber-400',
    completed: 'bg-emerald-400',
    failed: 'bg-rose-400',
  }

  return (
    <div className="space-y-1">
      {actions.map((action, i) => (
        <div key={i} className="flex items-start gap-3 py-2">
          <div className="flex flex-col items-center">
            <div className={`w-3 h-3 rounded-full ${statusColors[action.status] || 'bg-slate-400'} mt-1`} />
            {i < actions.length - 1 && <div className="w-px flex-1 bg-slate-200 my-1" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-900">{action.action_type}</span>
              <span className="text-xs text-slate-400">
                {action.scheduled_at ? new Date(action.scheduled_at).toLocaleString() : 'Unscheduled'}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span>Score: {action.priority_score.toFixed(2)}</span>
              <span>Reward: {(action.expected_reward * 100).toFixed(0)}%</span>
              <span className="capitalize">{action.status.replace('_', ' ')}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 9: Create `admin/src/pages/GrowthPage.tsx`**

```tsx
import { useState, useEffect } from 'react'
import { growthApi } from '../lib/api'
import GrowthOverview from '../components/GrowthOverview'
import TrajectoryChart from '../components/TrajectoryChart'
import OpportunityList from '../components/OpportunityList'
import ActionTimeline from '../components/ActionTimeline'
import type { GrowthState, Opportunity, ScheduledAction } from '../types'

export default function GrowthPage() {
  const [websiteId, setWebsiteId] = useState('')
  const [state, setState] = useState<GrowthState | null>(null)
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [scheduledActions, setScheduledActions] = useState<ScheduledAction[]>([])
  const [loading, setLoading] = useState(false)

  async function loadData() {
    if (!websiteId.trim()) return
    setLoading(true)
    try {
      const [stateRes, oppRes, schedRes] = await Promise.all([
        growthApi.getState(websiteId),
        growthApi.opportunities(websiteId, { score: 50, issues: 0, top_k: 5 }),
        growthApi.schedule(websiteId, { score: 50, issues: 0, max_actions: 5 }),
      ])
      setState(stateRes.data)
      setOpportunities(oppRes.data)
      setScheduledActions(schedRes.data)
    } catch (err) {
      console.error('Failed to load growth data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (websiteId) loadData()
  }, [websiteId])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Website Growth</h1>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Enter website ID..."
            value={websiteId}
            onChange={e => setWebsiteId(e.target.value)}
            className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-primary w-64"
          />
          <button
            onClick={loadData}
            disabled={!websiteId.trim()}
            className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Load
          </button>
        </div>
      </div>

      <div className="space-y-6">
        <GrowthOverview state={state} loading={loading} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TrajectoryChart scoreHistory={state?.score_history || []} loading={loading} />

          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <h3 className="text-sm font-medium text-slate-700 mb-4">Action Effectiveness</h3>
            {state?.action_effectiveness && Object.keys(state.action_effectiveness).length > 0 ? (
              <div className="space-y-2">
                {Object.entries(state.action_effectiveness).map(([action, stats]) => (
                  <div key={action} className="flex items-center justify-between py-1">
                    <span className="text-sm text-slate-700">{action}</span>
                    <span className="text-sm text-slate-500">
                      {stats.count}x &middot; {(stats.avg_reward * 100).toFixed(0)}% avg reward
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-slate-400">No action data yet</div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-medium text-slate-700 mb-3">Opportunities</h3>
            <OpportunityList opportunities={opportunities} loading={loading} />
          </div>
          <div>
            <h3 className="text-sm font-medium text-slate-700 mb-3">Scheduled Actions</h3>
            <ActionTimeline actions={scheduledActions} loading={loading} />
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 10: Verify the admin build**

Run: `cd admin && npm run build`
Expected: Build succeeds without errors

- [ ] **Step 11: Run all backend tests**

Run: `cd backend && python3 -m pytest tests/ -v`
Expected: All tests pass (existing + new)

- [ ] **Step 12: Commit**

```bash
git add admin/src/
git commit -m "feat: add Growth Dashboard frontend page with overview, chart, opportunities, timeline"
```

---

## Self-Review

### Spec Coverage
- **Growth Tracker Service**: ✅ Task 2 — `GrowthTracker` with growth state, comparison, intervention detection, effective actions
- **Opportunity Detector**: ✅ Task 3 — `OpportunityDetector` combining PPO policy + cross-site patterns + heuristics
- **Action Scheduler**: ✅ Task 4 — `ActionScheduler` with dedup, priority scoring, queue management
- **Growth Dashboard API**: ✅ Task 5 — 6 REST endpoints (state, compare, intervention, effective-actions, opportunities, schedule)
- **Production Decision Engine**: ✅ Task 6 — Enhanced DecisionIntegrator with logging, metrics, stats
- **Phase 3 Bug Fixes**: ✅ Task 1 — All 4 failing tests, lazy imports, auto_train_loop, missing exports

### Placeholder Scan
No TBD, TODO, or placeholder content found in any task code.

### Type Consistency
- `GrowthState.trend` matches `Literal["accelerating", "decelerating", "plateauing", "declining", "unknown"]` throughout
- `Opportunity` fields consistent between Python dataclass, API response, and TypeScript interface
- `ScheduledAction.status` consistent between Python and TypeScript
- `RewardCalculator.from_seo_results(previous_score, current_score)` signature matches all callers
