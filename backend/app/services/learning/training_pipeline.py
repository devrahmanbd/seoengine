import asyncio
from typing import Any

from app.services.atropos.scored_data_api import ScoredData, ScoredDataBuffer


class TrainingPipeline:
    def __init__(self, collector: Any = None, trainer: Any = None, buffer: ScoredDataBuffer | None = None):
        self._collector = collector
        self._trainer = trainer
        self._buffer = buffer or ScoredDataBuffer(max_size=10000)
        self._auto_train_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._stats: dict[str, Any] = {
            "total_training_runs": 0,
            "total_trajectories_collected": 0,
            "total_reward": 0.0,
            "avg_reward": 0.0,
            "last_training_stats": {},
        }

    def _transform_to_scored_data(self, trajectories: list) -> list[ScoredData]:
        scored: list[ScoredData] = []
        for traj in trajectories:
            for i in range(min(len(traj.states) - 1, len(traj.actions), len(traj.rewards))):
                scored.append(ScoredData(
                    state=traj.states[i],
                    action=traj.actions[i],
                    reward=traj.rewards[i],
                    next_state=traj.states[i + 1] if i + 1 < len(traj.states) else traj.states[-1],
                    done=(i == len(traj.rewards) - 1),
                ))
            if len(traj.states) == 1 and len(traj.actions) == 1 and len(traj.rewards) == 1:
                scored.append(ScoredData(
                    state=traj.states[0],
                    action=traj.actions[0],
                    reward=traj.rewards[0],
                    next_state=traj.states[0],
                    done=True,
                ))
        return scored

    async def collect_and_train(self, website_id: str) -> dict:
        if self._collector is None:
            return {"status": "no_collector", "website_id": website_id}

        trajectories = await self._collector.collect_website_trajectories(website_id)
        if not trajectories:
            return {"status": "no_data", "website_id": website_id, "trajectories": 0}

        scored_data = self._transform_to_scored_data(trajectories)
        self._buffer.extend(scored_data)

        self._stats["total_trajectories_collected"] += len(trajectories)
        total_reward = sum(t.rewards[0] for t in trajectories if t.rewards)
        self._stats["total_reward"] += total_reward

        training_stats: dict = {}
        if self._trainer is not None:
            try:
                training_stats = await self._trainer.update_policy(trajectories)
            except Exception:
                training_stats = {}
            self._stats["total_training_runs"] += 1
            self._stats["last_training_stats"] = training_stats

        avg_reward = total_reward / len(trajectories) if trajectories else 0.0
        self._stats["avg_reward"] = avg_reward

        return {
            "status": "success",
            "website_id": website_id,
            "trajectories": len(trajectories),
            "scored_data_added": len(scored_data),
            "training_stats": training_stats,
            "avg_reward": avg_reward,
        }

    async def collect_from_all_sites(self) -> dict:
        if self._collector is None:
            return {"status": "no_collector", "sites_trained": 0}

        trajectories = await self._collector.collect_all_trajectories()
        if not trajectories:
            return {"status": "no_data", "sites_trained": 0}

        scored_data = self._transform_to_scored_data(trajectories)
        self._buffer.extend(scored_data)

        self._stats["total_trajectories_collected"] += len(trajectories)
        total_reward = sum(sum(t.rewards) for t in trajectories)
        self._stats["total_reward"] += total_reward

        training_stats: dict = {}
        if self._trainer is not None:
            try:
                training_stats = await self._trainer.update_policy(trajectories)
            except Exception:
                training_stats = {}
            self._stats["total_training_runs"] += 1
            self._stats["last_training_stats"] = training_stats

        avg_reward = total_reward / len(trajectories) if trajectories else 0.0
        self._stats["avg_reward"] = avg_reward

        return {
            "status": "success",
            "sites_trained": 1,
            "trajectories": len(trajectories),
            "scored_data_added": len(scored_data),
            "training_stats": training_stats,
        }

    def add_to_buffer(self, scored: list[ScoredData]) -> None:
        self._buffer.extend(scored)

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    def get_training_stats(self) -> dict:
        return dict(self._stats)

    async def start_auto_train(self, interval: int = 3600) -> None:
        if self._auto_train_task is not None:
            return
        self._stop_event.clear()
        self._auto_train_task = asyncio.create_task(self._auto_train_loop(interval))

    async def _auto_train_loop(self, interval: int) -> None:
        while not self._stop_event.is_set():
            await self.collect_from_all_sites()
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    async def stop_auto_train(self) -> None:
        if self._auto_train_task is None:
            return
        self._stop_event.set()
        self._auto_train_task.cancel()
        try:
            await self._auto_train_task
        except asyncio.CancelledError:
            pass
        self._auto_train_task = None
