from dataclasses import dataclass
from threading import Lock
from typing import Any
import random

from fastapi import APIRouter, Query


@dataclass
class ScoredData:
    state: dict
    action: dict
    reward: float
    next_state: dict
    done: bool
    logprobs: dict | None = None
    distill_data: dict | None = None


class ScoredDataBuffer:
    def __init__(self, max_size: int = 10000) -> None:
        self._data: list[ScoredData] = []
        self._max_size = max_size
        self._lock = Lock()

    def append(self, data: ScoredData) -> None:
        with self._lock:
            if len(self._data) >= self._max_size:
                self._data.pop(0)
            self._data.append(data)

    def extend(self, data: list[ScoredData]) -> None:
        with self._lock:
            for item in data:
                if len(self._data) >= self._max_size:
                    self._data.pop(0)
                self._data.append(item)

    def sample(self, batch_size: int) -> list[ScoredData]:
        with self._lock:
            if len(self._data) == 0:
                return []
            actual = min(batch_size, len(self._data))
            return random.sample(self._data, actual)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


scored_data_buffer = ScoredDataBuffer()

ScoredDataAPI = APIRouter(prefix="/api/v1/atropos")


@ScoredDataAPI.post("/scored_data")
async def post_scored_data(data: dict) -> dict[str, Any]:
    sd = ScoredData(
        state=data["state"],
        action=data["action"],
        reward=data["reward"],
        next_state=data["next_state"],
        done=data["done"],
        logprobs=data.get("logprobs"),
        distill_data=data.get("distill_data"),
    )
    scored_data_buffer.append(sd)
    return {"status": "ok", "buffer_size": len(scored_data_buffer)}


@ScoredDataAPI.post("/scored_data_list")
async def post_scored_data_list(data: list[dict]) -> dict[str, Any]:
    items: list[ScoredData] = []
    for item in data:
        sd = ScoredData(
            state=item["state"],
            action=item["action"],
            reward=item["reward"],
            next_state=item["next_state"],
            done=item["done"],
            logprobs=item.get("logprobs"),
            distill_data=item.get("distill_data"),
        )
        items.append(sd)
    scored_data_buffer.extend(items)
    return {"status": "ok", "buffer_size": len(scored_data_buffer)}


@ScoredDataAPI.get("/batch")
async def get_batch(batch_size: int = Query(32, ge=1)) -> dict[str, Any]:
    items = scored_data_buffer.sample(batch_size)
    return {"items": items, "count": len(items)}


@ScoredDataAPI.get("/stats")
async def get_stats() -> dict[str, Any]:
    return {"buffer_size": len(scored_data_buffer)}
