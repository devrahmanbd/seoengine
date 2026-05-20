from uuid import uuid4

import torch
import torch.nn as nn

from app.embeddings import embed_text, cosine_similarity
from app.models import LoRAContext, EntityNode


class LoRAModule(nn.Module):
    def __init__(self, in_dim: int, rank: int = 8):
        super().__init__()
        self.in_dim = in_dim
        self.rank = rank
        self.lora_a = nn.Parameter(torch.randn(in_dim, rank) * 0.01)
        self.lora_b = nn.Parameter(torch.zeros(rank, in_dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + (x @ self.lora_a @ self.lora_b)

    @property
    def parameter_count(self) -> int:
        return self.lora_a.numel() + self.lora_b.numel()


class LoRASemanticAdapter:
    def __init__(self, embed_fn=None, cosine_fn=None, rank: int = 8, alpha: float = 0.5):
        self.rank = rank
        self.alpha = alpha
        self._adapters: dict[str, LoRAContext] = {}
        self._lora_modules: dict[str, LoRAModule] = {}
        self._embed = embed_fn or embed_text
        self._cosine = cosine_fn or cosine_similarity

    async def adapt(self, site_id: str, query: str, site_vector: list[float] | None = None) -> LoRAContext:
        query_vec = self._embed(query)
        if site_vector and len(site_vector) == len(query_vec):
            adapted = [
                q + self.alpha * (s - q)
                for q, s in zip(query_vec, site_vector)
            ]
        else:
            adapted = query_vec[:]
        adapter_id = str(uuid4())
        ctx = LoRAContext(
            adapter_id=adapter_id,
            site_id=site_id,
            query=query,
            adapted_embedding=adapted,
            confidence=0.0,
            metadata={
                "rank": self.rank,
                "alpha": self.alpha,
                "dimension": len(adapted),
            },
            top_entities=[],
        )
        self._adapters[adapter_id] = ctx
        return ctx

    async def train_step(
        self, site_id: str, query: str, reward: float, site_vector: list[float] | None = None, lr: float = 1e-3
    ) -> dict:
        if site_id not in self._lora_modules:
            in_dim = len(self._embed(query))
            self._lora_modules[site_id] = LoRAModule(in_dim=in_dim, rank=self.rank)

        module = self._lora_modules[site_id]
        optimizer = torch.optim.SGD(module.parameters(), lr=lr)

        if site_vector and len(site_vector) > 0:
            query_tensor = torch.tensor(self._embed(query), dtype=torch.float32)
            site_tensor = torch.tensor(site_vector, dtype=torch.float32)
            adapted_tensor = module(query_tensor)
            sim = torch.cosine_similarity(
                adapted_tensor.unsqueeze(0), site_tensor.unsqueeze(0)
            )
            loss = -reward * sim
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(module.parameters(), max_norm=1.0)
            optimizer.step()
        else:
            sim = torch.tensor(0.0)
            loss = torch.tensor(0.0)

        return {"loss": round(loss.item(), 6), "reward": reward}

    def save(self, path: str) -> None:
        data = {}
        for site_id, module in self._lora_modules.items():
            data[site_id] = {
                "in_dim": module.in_dim,
                "rank": module.rank,
                "state_dict": module.state_dict(),
            }
        torch.save(data, path)

    def load(self, path: str) -> None:
        data = torch.load(path, map_location="cpu", weights_only=True)
        for site_id, info in data.items():
            module = LoRAModule(in_dim=info["in_dim"], rank=info["rank"])
            module.load_state_dict(info["state_dict"])
            self._lora_modules[site_id] = module

    async def get_adapter(self, adapter_id: str) -> LoRAContext | None:
        return self._adapters.get(adapter_id)

    async def list_adapters(self, site_id: str | None = None) -> list[LoRAContext]:
        if site_id:
            return [c for c in self._adapters.values() if c.site_id == site_id]
        return list(self._adapters.values())

    async def health(self) -> dict:
        return {
            "status": "healthy",
            "adapter_count": len(self._adapters),
            "lora_module_count": len(self._lora_modules),
            "rank": self.rank,
            "alpha": self.alpha,
        }
