import os
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class MLClient:
    def __init__(self) -> None:
        self._base_url = os.environ.get("ML_SERVICE_URL", "http://ml-service:8000")
        self._api_key = settings.ml_api_key if hasattr(settings, "ml_api_key") else ""
        self._client = httpx.AsyncClient(timeout=30.0)
        self._enabled = os.environ.get("ML_ENABLED", "true").lower() == "true"

    async def is_available(self) -> bool:
        if not self._enabled:
            return False
        try:
            r = await self._client.get(
                f"{self._base_url}/v1/ml/health",
                headers={"X-API-Key": self._api_key} if self._api_key else {},
                timeout=5.0,
            )
            return r.status_code == 200 and r.json().get("status") == "ok"
        except Exception:
            return False

    async def get_status(self) -> dict:
        if not self._enabled:
            return {"available": False, "reason": "ML service disabled"}
        try:
            r = await self._client.get(
                f"{self._base_url}/v1/ml/status",
                headers={"X-API-Key": self._api_key} if self._api_key else {},
                timeout=5.0,
            )
            if r.status_code == 200:
                data = r.json()
                data["available"] = True
                return data
            return {"available": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"available": False, "error": str(e)}

    async def recommend(self, state: dict, top_k: int = 3) -> list[dict]:
        if not self._enabled:
            return self._empty_recommendations()
        try:
            r = await self._client.post(
                f"{self._base_url}/v1/ml/recommend",
                json={"state": state, "top_k": top_k},
                headers={"X-API-Key": self._api_key} if self._api_key else {},
                timeout=10.0,
            )
            if r.status_code == 200:
                return r.json().get("recommendations", [])
            return self._empty_recommendations()
        except Exception as e:
            logger.warning("ML recommend failed: %s", e)
            return self._empty_recommendations()

    async def train(self, trajectories: list[dict]) -> dict:
        if not self._enabled:
            return {"status": "skipped", "reason": "ML service disabled"}
        try:
            r = await self._client.post(
                f"{self._base_url}/v1/ml/train",
                json=trajectories,
                headers={"X-API-Key": self._api_key} if self._api_key else {},
                timeout=60.0,
            )
            if r.status_code == 200:
                return r.json()
            return {"status": "error", "detail": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def adapt(self, site_id: str, query: str, site_vector: list[float] | None = None) -> dict | None:
        if not self._enabled:
            return None
        try:
            r = await self._client.post(
                f"{self._base_url}/v1/ml/adapt",
                json={"site_id": site_id, "query": query, "site_vector": site_vector},
                headers={"X-API-Key": self._api_key} if self._api_key else {},
                timeout=15.0,
            )
            if r.status_code == 200:
                return r.json().get("value")
            return None
        except Exception as e:
            logger.warning("ML adapt failed: %s", e)
            return None

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not self._enabled:
            return []
        try:
            r = await self._client.post(
                f"{self._base_url}/v1/ml/embed",
                json={"texts": texts},
                headers={"X-API-Key": self._api_key} if self._api_key else {},
                timeout=15.0,
            )
            if r.status_code == 200:
                return r.json().get("embeddings", [])
            return []
        except Exception as e:
            logger.warning("ML embed failed: %s", e)
            return []

    async def cluster_vectors(self, vectors: list[list[float]], site_ids: list[str]) -> list[list[str]]:
        if not self._enabled:
            return []
        try:
            r = await self._client.post(
                f"{self._base_url}/v1/ml/cluster",
                json={"vectors": vectors, "site_ids": site_ids},
                headers={"X-API-Key": self._api_key} if self._api_key else {},
                timeout=30.0,
            )
            if r.status_code == 200:
                return r.json().get("clusters", [])
            return []
        except Exception as e:
            logger.warning("ML cluster failed: %s", e)
            return []

    async def find_shared_entities(
        self, cluster: list[str], site_entities: dict[str, list[dict]]
    ) -> list[dict]:
        if not self._enabled:
            return []
        try:
            r = await self._client.post(
                f"{self._base_url}/v1/ml/shared-entities",
                json={"cluster": cluster, "site_entities": site_entities},
                headers={"X-API-Key": self._api_key} if self._api_key else {},
                timeout=30.0,
            )
            if r.status_code == 200:
                return r.json().get("patterns", [])
            return []
        except Exception as e:
            logger.warning("ML shared-entities failed: %s", e)
            return []

    def _empty_recommendations(self) -> list[dict]:
        return []

    async def toggle(self, enabled: bool) -> None:
        self._enabled = enabled
        logger.info("ML service toggled %s", "ON" if enabled else "OFF")

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def close(self) -> None:
        await self._client.aclose()
