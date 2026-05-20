from dataclasses import dataclass
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical


@dataclass
class Trajectory:
    states: list[dict]
    actions: list[dict]
    rewards: list[float]
    logprobs: list[dict] | None = None


class PolicyNetwork(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
        )

    def forward(self, x: torch.Tensor) -> Categorical:
        return Categorical(logits=self.net(x))


class ValueNetwork(nn.Module):
    def __init__(self, state_dim: int, hidden_dim: int = 256) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


class PPOTrainer:
    def __init__(
        self,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        target_kl: float = 0.02,
        entropy_coef: float = 0.01,
        value_coef: float = 0.5,
        max_grad_norm: float = 0.5,
        epochs: int = 4,
        mini_batch_size: int = 64,
        state_dim: int = 128,
        action_dim: int = 6,
        hidden_dim: int = 256,
        anneal_lr: bool = True,
    ) -> None:
        self.lr = lr
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.target_kl = target_kl
        self.entropy_coef = entropy_coef
        self.value_coef = value_coef
        self.max_grad_norm = max_grad_norm
        self.epochs = epochs
        self.mini_batch_size = mini_batch_size
        self.anneal_lr = anneal_lr

        self._state_dim = state_dim
        self._action_dim = action_dim
        self._hidden_dim = hidden_dim

        self._policy = PolicyNetwork(state_dim, action_dim, hidden_dim)
        self._value = ValueNetwork(state_dim, hidden_dim)
        self._optimizer = optim.Adam(
            list(self._policy.parameters()) + list(self._value.parameters()),
            lr=lr,
        )
        self._scheduler = (
            optim.lr_scheduler.CosineAnnealingLR(
                self._optimizer, T_max=1000, eta_min=lr * 0.01
            )
            if anneal_lr
            else None
        )

        self._action_registry: dict[str, int] = {}
        self._train_step = 0

    # ------------------------------------------------------------------
    # State / action conversion helpers
    # ------------------------------------------------------------------

    def _state_to_tensor(self, state: dict) -> torch.Tensor:
        features = state.get("features")
        if isinstance(features, list) and len(features) > 0:
            f = features[: self._state_dim]
            if len(f) < self._state_dim:
                f = f + [0.0] * (self._state_dim - len(f))
            return torch.tensor(f, dtype=torch.float32)

        metrics = state.get("metrics", {})
        if isinstance(metrics, dict):
            flat = [float(v) for v in metrics.values() if isinstance(v, (int, float))]
            flat = [max(0.0, min(1.0, v)) for v in flat]
            if len(flat) >= self._state_dim:
                return torch.tensor(flat[: self._state_dim], dtype=torch.float32)
            flat += [0.0] * (self._state_dim - len(flat))
            return torch.tensor(flat, dtype=torch.float32)

        return torch.zeros(self._state_dim, dtype=torch.float32)

    def _get_action_idx(self, action: dict) -> int:
        action_type = action.get("action_type", "")
        idx = self._action_registry.get(action_type)
        if idx is not None:
            return idx
        next_idx = len(self._action_registry)
        if next_idx < self._action_dim:
            self._action_registry[action_type] = next_idx
            return next_idx
        self._action_registry[action_type] = hash(action_type) % self._action_dim
        return self._action_registry[action_type]

    def _extract_logprob(self, logprob_data: dict | None) -> float:
        if logprob_data is not None:
            return float(logprob_data.get("logprob", 0.0))
        return 0.0

    # ------------------------------------------------------------------
    # GAE computation  (preserved for backward compat)
    # ------------------------------------------------------------------

    async def compute_gae(
        self, rewards: list[float], values: list[float], dones: list[bool]
    ) -> list[float]:
        gae = 0.0
        advantages: list[float] = []
        for t in reversed(range(len(rewards))):
            next_val = 0.0 if t == len(rewards) - 1 or dones[t] else values[t + 1]
            delta = rewards[t] + self.gamma * next_val - values[t]
            gae = delta + self.gamma * self.gae_lambda * (0.0 if dones[t] else gae)
            advantages.insert(0, gae)
        return advantages

    # ------------------------------------------------------------------
    # Core PPO clipped surrogate objective
    # ------------------------------------------------------------------

    def _compute_ppo_loss(
        self,
        states: torch.Tensor,
        actions: torch.Tensor,
        old_logprobs: torch.Tensor,
        advantages: torch.Tensor,
        returns: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        dist = self._policy(states)
        log_probs = dist.log_prob(actions)
        entropy = dist.entropy().mean()

        ratios = torch.exp(log_probs - old_logprobs)
        surr1 = ratios * advantages
        surr2 = (
            torch.clamp(ratios, 1.0 - self.clip_epsilon, 1.0 + self.clip_epsilon)
            * advantages
        )
        policy_loss = -torch.min(surr1, surr2).mean()

        values_pred = self._value(states)
        value_loss = F.mse_loss(values_pred, returns)

        with torch.no_grad():
            clip_fraction = ((ratios - 1.0).abs() > self.clip_epsilon).float().mean()

        return policy_loss, value_loss, entropy, clip_fraction

    def _zero_stats(self) -> dict:
        return {
            "policy_loss": 0.0,
            "value_loss": 0.0,
            "entropy": 0.0,
            "kl": 0.0,
            "clip_fraction": 0.0,
        }

    # ------------------------------------------------------------------
    # Multi-trajectory batch preparation (full GAE)
    # ------------------------------------------------------------------

    def _prepare_trajectory_batch(
        self, trajectories: list[Trajectory]
    ) -> (
        tuple[
            torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor
        ]
        | None
    ):
        states_list: list[torch.Tensor] = []
        actions_list: list[int] = []
        old_logprobs_list: list[float] = []
        traj_lens: list[int] = []
        traj_rewards: list[list[float]] = []

        for traj in trajectories:
            n = len(traj.states)
            if n == 0:
                continue
            for i in range(n):
                states_list.append(self._state_to_tensor(traj.states[i]))
                actions_list.append(self._get_action_idx(traj.actions[i]))
                old_logprobs_list.append(
                    self._extract_logprob(traj.logprobs[i])
                    if traj.logprobs and i < len(traj.logprobs)
                    else 0.0
                )
            traj_lens.append(n)
            traj_rewards.append(traj.rewards)

        if not states_list:
            return None

        states = torch.stack(states_list)
        actions = torch.tensor(actions_list, dtype=torch.long)
        old_logprobs = torch.tensor(old_logprobs_list, dtype=torch.float32)

        with torch.no_grad():
            values = self._value(states)

        advantages_list: list[float] = []
        returns_list: list[float] = []
        offset = 0

        for t_len, rewards in zip(traj_lens, traj_rewards):
            seg_values = values[offset : offset + t_len]
            gae = 0.0
            for t in reversed(range(t_len)):
                next_val = (
                    0.0
                    if t == t_len - 1
                    else seg_values[t + 1].item()
                )
                delta = rewards[t] + self.gamma * next_val - seg_values[t].item()
                gae = delta + self.gamma * self.gae_lambda * gae
                advantages_list.insert(offset, gae)
                returns_list.insert(offset, seg_values[t].item() + gae)
            offset += t_len

        advantages = torch.tensor(advantages_list, dtype=torch.float32)
        returns = torch.tensor(returns_list, dtype=torch.float32)

        return states, actions, old_logprobs, advantages, returns

    # ------------------------------------------------------------------
    # Inner PPO epoch loop
    # ------------------------------------------------------------------

    def _ppo_update(
        self,
        states: torch.Tensor,
        actions: torch.Tensor,
        old_logprobs: torch.Tensor,
        advantages: torch.Tensor,
        returns: torch.Tensor,
    ) -> dict:
        n = len(states)
        agg = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0, "kl": 0.0, "clip_fraction": 0.0}
        n_updates = 0

        for epoch in range(self.epochs):
            with torch.no_grad():
                epoch_start_logits = self._policy(states).logits

            indices = torch.randperm(n)
            for start in range(0, n, self.mini_batch_size):
                idx = indices[start : start + self.mini_batch_size]
                p_loss, v_loss, ent, cf = self._compute_ppo_loss(
                    states[idx],
                    actions[idx],
                    old_logprobs[idx],
                    advantages[idx],
                    returns[idx],
                )

                loss = p_loss + self.value_coef * v_loss - self.entropy_coef * ent

                self._optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(
                    list(self._policy.parameters())
                    + list(self._value.parameters()),
                    self.max_grad_norm,
                )
                self._optimizer.step()

                agg["policy_loss"] += p_loss.item()
                agg["value_loss"] += v_loss.item()
                agg["entropy"] += ent.item()
                agg["clip_fraction"] += cf.item()
                n_updates += 1

            with torch.no_grad():
                epoch_end_logits = self._policy(states).logits
                logp_old = epoch_start_logits.log_softmax(-1)
                logp_new = epoch_end_logits.log_softmax(-1)
                kl = (logp_old.exp() * (logp_old - logp_new)).sum(-1).mean().item()
                agg["kl"] += kl

            if kl > self.target_kl:
                break

        if n_updates > 0:
            for k in agg:
                agg[k] /= n_updates

        self._train_step += 1
        return agg

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def update_policy(self, trajectories: list[Trajectory]) -> dict:
        if not trajectories:
            return self._zero_stats()

        batch = self._prepare_trajectory_batch(trajectories)
        if batch is None:
            return self._zero_stats()

        states, actions, old_logprobs, advantages, returns = batch

        if advantages.numel() > 1 and advantages.std() > 1e-8:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        self._policy.train()
        self._value.train()
        stats = self._ppo_update(states, actions, old_logprobs, advantages, returns)

        if self.anneal_lr and self._scheduler is not None:
            self._scheduler.step()

        return stats

    async def train_on_buffer(
        self, buffer: "ScoredDataBuffer", batch_size: int = 32
    ) -> dict:
        items = buffer.sample(batch_size)
        if not items:
            return self._zero_stats()

        states_list: list[torch.Tensor] = []
        actions_list: list[int] = []
        old_logprobs_list: list[float] = []
        rewards_list: list[float] = []
        next_states_list: list[torch.Tensor] = []
        dones_list: list[bool] = []

        for item in items:
            states_list.append(self._state_to_tensor(item.state))
            actions_list.append(self._get_action_idx(item.action))
            rewards_list.append(item.reward)
            next_states_list.append(self._state_to_tensor(item.next_state))
            dones_list.append(item.done)
            old_logprobs_list.append(self._extract_logprob(item.logprobs))

        states = torch.stack(states_list)
        actions = torch.tensor(actions_list, dtype=torch.long)
        rewards = torch.tensor(rewards_list, dtype=torch.float32)
        next_states = torch.stack(next_states_list)
        dones = torch.tensor(dones_list, dtype=torch.float32)
        old_logprobs = torch.tensor(old_logprobs_list, dtype=torch.float32)

        with torch.no_grad():
            values = self._value(states)
            next_values = self._value(next_states)

        advantages = rewards + self.gamma * next_values * (1.0 - dones) - values
        returns = advantages + values

        if advantages.numel() > 1 and advantages.std() > 1e-8:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        self._policy.train()
        self._value.train()
        stats = self._ppo_update(states, actions, old_logprobs, advantages, returns)

        if self.anneal_lr and self._scheduler is not None:
            self._scheduler.step()

        return stats

    # ------------------------------------------------------------------
    # Model persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        data: dict[str, Any] = {
            "hyperparams": {
                "lr": self.lr,
                "gamma": self.gamma,
                "gae_lambda": self.gae_lambda,
                "clip_epsilon": self.clip_epsilon,
                "target_kl": self.target_kl,
                "entropy_coef": self.entropy_coef,
                "value_coef": self.value_coef,
                "max_grad_norm": self.max_grad_norm,
                "epochs": self.epochs,
                "mini_batch_size": self.mini_batch_size,
                "state_dim": self._state_dim,
                "action_dim": self._action_dim,
                "hidden_dim": self._hidden_dim,
            },
            "policy_state_dict": self._policy.state_dict(),
            "value_state_dict": self._value.state_dict(),
            "optimizer_state_dict": self._optimizer.state_dict(),
            "scheduler_state_dict": (
                self._scheduler.state_dict() if self._scheduler else None
            ),
            "action_registry": self._action_registry,
            "train_step": self._train_step,
        }
        torch.save(data, path)

    def load(self, path: str) -> None:
        data = torch.load(path, map_location="cpu", weights_only=True)
        self._policy.load_state_dict(data["policy_state_dict"])
        self._value.load_state_dict(data["value_state_dict"])
        self._optimizer.load_state_dict(data["optimizer_state_dict"])
        if data.get("scheduler_state_dict") and self._scheduler:
            self._scheduler.load_state_dict(data["scheduler_state_dict"])
        self._action_registry = data.get("action_registry", {})
        self._train_step = data.get("train_step", 0)
