from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any
import time


@dataclass
class SEOAction:
    action_type: str
    params: dict
    confidence: float = 0.0


@dataclass
class State:
    site_id: str
    metrics: dict
    timestamp: float
    features: list[float] | None = None


class SEOEnvironment(ABC):
    @abstractmethod
    async def reset(self) -> State:
        ...

    @abstractmethod
    async def step(self, action: SEOAction) -> tuple[State, float, bool, dict]:
        ...

    async def render(self) -> dict:
        return {"metrics": {}, "timestamp": time.time()}

    async def close(self) -> None:
        ...


class Registry:
    _environments: dict[str, type[SEOEnvironment]] = {}

    @classmethod
    def register(cls, name: str, env_class: type[SEOEnvironment]) -> None:
        cls._environments[name] = env_class

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> SEOEnvironment:
        if name not in cls._environments:
            raise ValueError(f"Environment '{name}' not registered")
        return cls._environments[name](**kwargs)

    @classmethod
    def list(cls) -> list[str]:
        return list(cls._environments.keys())
