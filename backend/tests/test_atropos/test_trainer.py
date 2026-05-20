import pytest
import torch
from app.services.atropos.trainer import PPOTrainer, Trajectory, PolicyNetwork, ValueNetwork


@pytest.fixture
def trainer():
    return PPOTrainer(lr=1e-3, gamma=0.99, gae_lambda=0.95, clip_epsilon=0.2, epochs=4)


class TestPolicyNetwork:
    def test_creation(self):
        net = PolicyNetwork(state_dim=128, action_dim=6)
        assert isinstance(net, PolicyNetwork)

    def test_forward_returns_categorical(self):
        net = PolicyNetwork(state_dim=128, action_dim=6)
        x = torch.randn(4, 128)
        dist = net(x)
        assert dist.probs.shape == (4, 6)
        assert dist.probs.sum(-1).allclose(torch.ones(4))


class TestValueNetwork:
    def test_creation(self):
        net = ValueNetwork(state_dim=128)
        assert isinstance(net, ValueNetwork)

    def test_forward_returns_scalar_per_batch(self):
        net = ValueNetwork(state_dim=128)
        x = torch.randn(4, 128)
        out = net(x)
        assert out.shape == (4,)


class TestTrajectory:
    def test_defaults(self):
        t = Trajectory(states=[], actions=[], rewards=[])
        assert t.logprobs is None

    def test_custom_logprobs(self):
        t = Trajectory(states=[], actions=[], rewards=[], logprobs=[{"p": 0.5}])
        assert t.logprobs == [{"p": 0.5}]


class TestPPOTrainer:
    @pytest.mark.asyncio
    async def test_compute_gae_simple(self, trainer):
        rewards = [1.0, 1.0, 1.0]
        values = [0.5, 0.5, 0.5]
        dones = [False, False, True]
        advantages = await trainer.compute_gae(rewards, values, dones)
        assert len(advantages) == 3
        assert all(isinstance(a, float) for a in advantages)

    @pytest.mark.asyncio
    async def test_compute_gae_all_done(self, trainer):
        rewards = [1.0, 1.0]
        values = [0.5, 0.5]
        dones = [True, True]
        advantages = await trainer.compute_gae(rewards, values, dones)
        assert len(advantages) == 2

    @pytest.mark.asyncio
    async def test_compute_gae_empty(self, trainer):
        advantages = await trainer.compute_gae([], [], [])
        assert advantages == []

    @pytest.mark.asyncio
    async def test_compute_gae_known_values(self, trainer):
        gamma = 0.99
        gae_lambda = 0.95
        trainer.gamma = gamma
        trainer.gae_lambda = gae_lambda
        rewards = [0.0, 10.0]
        values = [5.0, 8.0]
        dones = [False, True]
        advantages = await trainer.compute_gae(rewards, values, dones)
        delta_1 = rewards[1] + gamma * 0.0 - values[1]
        expected_adv_1 = delta_1
        delta_0 = rewards[0] + gamma * values[1] - values[0]
        expected_adv_0 = delta_0 + gamma * gae_lambda * expected_adv_1
        assert len(advantages) == 2
        assert abs(advantages[1] - expected_adv_1) < 1e-6
        assert abs(advantages[0] - expected_adv_0) < 1e-6

    @pytest.mark.asyncio
    async def test_compute_gae_no_done_uses_next_value(self, trainer):
        gamma = 0.99
        gae_lambda = 0.95
        trainer.gamma = gamma
        trainer.gae_lambda = gae_lambda
        rewards = [5.0, 5.0, 5.0]
        values = [3.0, 3.0, 3.0]
        dones = [False, False, False]
        advantages = await trainer.compute_gae(rewards, values, dones)
        assert len(advantages) == 3
        delta_2 = rewards[2] + gamma * 0.0 - values[2]
        expected_adv_2 = delta_2
        delta_1 = rewards[1] + gamma * values[2] - values[1]
        expected_adv_1 = delta_1 + gamma * gae_lambda * expected_adv_2
        delta_0 = rewards[0] + gamma * values[1] - values[0]
        expected_adv_0 = delta_0 + gamma * gae_lambda * expected_adv_1
        assert abs(advantages[2] - expected_adv_2) < 1e-6
        assert abs(advantages[1] - expected_adv_1) < 1e-6
        assert abs(advantages[0] - expected_adv_0) < 1e-6

    def _make_state(self, i: int) -> dict:
        return {"features": [float(i)] * 128, "metrics": {"score": float(i)}}

    def _make_action(self, action_type: str = "fix_title") -> dict:
        return {"action_type": action_type, "params": {}}

    @pytest.mark.asyncio
    async def test_update_policy_all_zero_rewards(self, trainer):
        traj = Trajectory(
            states=[self._make_state(0)],
            actions=[self._make_action("fix_title")],
            rewards=[0.0],
        )
        result = await trainer.update_policy([traj])
        assert all(k in result for k in ("policy_loss", "value_loss", "entropy", "kl", "clip_fraction"))
        assert isinstance(result["policy_loss"], float)
        assert result["value_loss"] >= 0.0

    @pytest.mark.asyncio
    async def test_update_policy_single_step_trajectory(self, trainer):
        traj = Trajectory(
            states=[self._make_state(1)],
            actions=[self._make_action("fix_title")],
            rewards=[1.0],
            logprobs=[{"logprob": -0.5}],
        )
        result = await trainer.update_policy([traj])
        assert all(k in result for k in ("policy_loss", "value_loss", "entropy", "kl", "clip_fraction"))

    @pytest.mark.asyncio
    async def test_update_policy_single_trajectory(self, trainer):
        traj = Trajectory(
            states=[self._make_state(1), self._make_state(2)],
            actions=[self._make_action("fix_title"), self._make_action("fix_meta")],
            rewards=[1.0, 0.5],
        )
        result = await trainer.update_policy([traj])
        assert all(k in result for k in ("policy_loss", "value_loss", "entropy", "kl", "clip_fraction"))
        assert isinstance(result["policy_loss"], float)
        assert result["value_loss"] >= 0.0

    @pytest.mark.asyncio
    async def test_update_policy_multiple_trajectories(self, trainer):
        trajectories = [
            Trajectory(
                states=[self._make_state(1)],
                actions=[self._make_action("fix_title")],
                rewards=[1.0],
            ),
            Trajectory(
                states=[self._make_state(2)],
                actions=[self._make_action("fix_meta")],
                rewards=[0.5],
            ),
            Trajectory(
                states=[self._make_state(3)],
                actions=[self._make_action("add_schema")],
                rewards=[0.0],
            ),
        ]
        result = await trainer.update_policy(trajectories)
        assert all(k in result for k in ("policy_loss", "value_loss", "entropy", "kl", "clip_fraction"))
        assert isinstance(result["policy_loss"], float)

    @pytest.mark.asyncio
    async def test_update_policy_empty(self, trainer):
        result = await trainer.update_policy([])
        assert result == {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0, "kl": 0.0, "clip_fraction": 0.0}

    @pytest.mark.asyncio
    async def test_train_on_buffer_empty(self, trainer):
        from app.services.atropos.scored_data_api import ScoredDataBuffer
        buffer = ScoredDataBuffer(max_size=10)
        result = await trainer.train_on_buffer(buffer)
        assert result == {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0, "kl": 0.0, "clip_fraction": 0.0}

    @pytest.mark.asyncio
    async def test_train_on_buffer_with_data(self, trainer):
        from app.services.atropos.scored_data_api import ScoredDataBuffer, ScoredData
        buffer = ScoredDataBuffer(max_size=10)
        for i in range(5):
            buffer.append(
                ScoredData(
                    state=self._make_state(i),
                    action=self._make_action("fix_title"),
                    reward=float(i),
                    next_state=self._make_state(i + 1),
                    done=False,
                    logprobs={"logprob": -0.1 * i},
                )
            )
        result = await trainer.train_on_buffer(buffer, batch_size=5)
        assert all(k in result for k in ("policy_loss", "value_loss", "entropy", "kl", "clip_fraction"))
        assert isinstance(result["policy_loss"], float)

    def test_save_and_load(self, trainer, tmp_path):
        path = str(tmp_path / "policy.pt")
        trainer.save(path)

        trainer2 = PPOTrainer(
            lr=trainer.lr,
            gamma=trainer.gamma,
            gae_lambda=trainer.gae_lambda,
            clip_epsilon=trainer.clip_epsilon,
            epochs=trainer.epochs,
        )
        trainer2.load(path)

        w1 = dict(trainer._policy.named_parameters())
        w2 = dict(trainer2._policy.named_parameters())
        for key in w1:
            assert torch.equal(w1[key], w2[key]), f"Mismatch in {key}"

        w1v = dict(trainer._value.named_parameters())
        w2v = dict(trainer2._value.named_parameters())
        for key in w1v:
            assert torch.equal(w1v[key], w2v[key]), f"Mismatch in {key}"

        assert trainer2._train_step == trainer._train_step
        assert trainer2._action_registry == trainer._action_registry

    @pytest.mark.asyncio
    async def test_state_to_tensor_with_features(self, trainer):
        state = {"features": [0.5] * 128}
        tensor = trainer._state_to_tensor(state)
        assert tensor.shape == (128,)
        assert tensor[0] == 0.5

    @pytest.mark.asyncio
    async def test_state_to_tensor_with_metrics(self, trainer):
        state = {"metrics": {"score": 0.8, "count": 10}}
        tensor = trainer._state_to_tensor(state)
        assert tensor.shape == (128,)

    @pytest.mark.asyncio
    async def test_state_to_tensor_mixed_metrics(self, trainer):
        state = {
            "metrics": {
                "score": 0.8,
                "count": 10,
                "label": "test",
                "flag": None,
                "valid": True,
            }
        }
        tensor = trainer._state_to_tensor(state)
        assert tensor.shape == (128,)
        assert tensor[0] == 0.8
        assert tensor[1] == 1.0
        assert tensor[2] == 1.0

    @pytest.mark.asyncio
    async def test_state_to_tensor_fallback(self, trainer):
        state = {"s": 1}
        tensor = trainer._state_to_tensor(state)
        assert tensor.shape == (128,)
        assert tensor.sum() == 0.0

    def test_get_action_idx_tracks_action_types(self, trainer):
        idx1 = trainer._get_action_idx({"action_type": "fix_title"})
        idx2 = trainer._get_action_idx({"action_type": "fix_meta"})
        idx3 = trainer._get_action_idx({"action_type": "fix_title"})
        assert idx1 == 0
        assert idx2 == 1
        assert idx3 == 0

    def test_extract_logprob(self, trainer):
        assert trainer._extract_logprob({"logprob": -0.5}) == -0.5
        assert trainer._extract_logprob(None) == 0.0
        assert trainer._extract_logprob({}) == 0.0
