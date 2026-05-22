import pytest
from app.learning.reward_calculator import RewardCalculator, Reward


class TestReward:
    def test_defaults(self):
        r = Reward(value=0.5)
        assert r.components == {}
        assert r.metadata is None

    def test_all_fields(self):
        r = Reward(value=1.0, components={"a": 0.5}, metadata={"k": "v"})
        assert r.value == 1.0
        assert r.components == {"a": 0.5}
        assert r.metadata == {"k": "v"}


class TestFromSEOResults:
    def test_score_increase(self):
        r = RewardCalculator.from_seo_results(50, 75)
        assert r.value > 0
        assert r.components["score_delta"] == 25

    def test_score_decrease(self):
        r = RewardCalculator.from_seo_results(80, 60)
        assert r.value < 0
        assert r.components["score_delta"] == -20

    def test_no_change(self):
        r = RewardCalculator.from_seo_results(50, 50)
        assert r.value == 0.0
        assert r.components["score_delta"] == 0

    def test_max_increase(self):
        r = RewardCalculator.from_seo_results(0, 100)
        assert r.value == 1.0

    def test_max_decrease(self):
        r = RewardCalculator.from_seo_results(100, 0)
        assert r.value == -1.0

    def test_none_previous(self):
        r = RewardCalculator.from_seo_results(None, 50)
        assert r.value == 0.0

    def test_none_current(self):
        r = RewardCalculator.from_seo_results(50, None)
        assert r.value == 0.0

    def test_both_none(self):
        r = RewardCalculator.from_seo_results(None, None)
        assert r.value == 0.0

    def test_metadata(self):
        r = RewardCalculator.from_seo_results(30, 45)
        assert r.metadata == {"previous_score": 30, "current_score": 45}


class TestFromTaskResult:
    def test_completed(self):
        r = RewardCalculator.from_task_result("completed", "fix_title")
        assert r.value > 0

    def test_success(self):
        r = RewardCalculator.from_task_result("success", "optimize_content")
        assert r.value > 0

    def test_failed(self):
        r = RewardCalculator.from_task_result("failed", "fix_title")
        assert r.value < 0

    def test_error(self):
        r = RewardCalculator.from_task_result("error")
        assert r.value < 0

    def test_timeout(self):
        r = RewardCalculator.from_task_result("timeout")
        assert r.value < 0
        assert r.value == -0.5

    def test_no_task_type(self):
        r = RewardCalculator.from_task_result("completed")
        assert r.value == 1.0

    def test_unknown_status(self):
        r = RewardCalculator.from_task_result("unknown_status")
        assert r.value == 0.0


class TestFromIssues:
    def test_issue_reduction(self):
        r = RewardCalculator.from_issues(10, 3)
        assert r.value > 0

    def test_issue_increase(self):
        r = RewardCalculator.from_issues(3, 10)
        assert r.value < 0

    def test_no_change(self):
        r = RewardCalculator.from_issues(5, 5)
        assert r.value == 0.0

    def test_all_issues_fixed(self):
        r = RewardCalculator.from_issues(5, 0)
        assert r.value > 0

    def test_none_previous(self):
        r = RewardCalculator.from_issues(None, 5)
        assert r.value == 0.0

    def test_none_current(self):
        r = RewardCalculator.from_issues(5, None)
        assert r.value == 0.0

    def test_zero_previous(self):
        r = RewardCalculator.from_issues(0, 5)
        assert r.value < 0


class TestCombined:
    def test_equal_weight(self):
        r1 = Reward(value=1.0, components={"a": 1.0})
        r2 = Reward(value=-1.0, components={"b": -1.0})
        combined = RewardCalculator.combined(r1, r2)
        assert combined.value == 0.0

    def test_custom_weights(self):
        r1 = Reward(value=1.0)
        r2 = Reward(value=0.0)
        combined = RewardCalculator.combined(r1, r2, weights=[1.0, 0.0])
        assert combined.value == 1.0

    def test_empty_rewards(self):
        combined = RewardCalculator.combined()
        assert combined.value == 0.0
        assert combined.components == {}

    def test_single_reward(self):
        r = Reward(value=0.75)
        combined = RewardCalculator.combined(r)
        assert combined.value == 0.75

    def test_weights_mismatch(self):
        r1 = Reward(value=1.0)
        r2 = Reward(value=0.5)
        combined = RewardCalculator.combined(r1, r2, weights=[1.0])
        assert combined.value > 0

    def test_all_zero_weights(self):
        r1 = Reward(value=1.0)
        r2 = Reward(value=1.0)
        combined = RewardCalculator.combined(r1, r2, weights=[0.0, 0.0])
        assert combined.value == 0.0

    def test_clamps_values(self):
        r1 = Reward(value=100.0)
        r2 = Reward(value=-100.0)
        combined = RewardCalculator.combined(r1, r2)
        assert -1.0 <= combined.value <= 1.0

    def test_components_merged(self):
        r1 = Reward(value=0.5, components={"a": 0.5})
        r2 = Reward(value=0.3, components={"b": 0.3})
        combined = RewardCalculator.combined(r1, r2)
        assert "a" in combined.components
        assert "b" in combined.components
