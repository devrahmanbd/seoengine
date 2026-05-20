from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.semantic import (
    SemanticDB,
    LoRASemanticAdapter,
    CrossSiteAnalyzer,
)

router = APIRouter(prefix="/api/v1/semantic", tags=["semantic"])


class ContextRequest(BaseModel):
    site_id: str
    query: str


class AdaptRequest(BaseModel):
    site_id: str
    query: str

_semantic_db: SemanticDB | None = None
_lora_adapter: LoRASemanticAdapter | None = None
_cross_analyzer: CrossSiteAnalyzer | None = None


def _get_db() -> SemanticDB:
    global _semantic_db
    if _semantic_db is None:
        _semantic_db = SemanticDB(dimension=32)
    return _semantic_db


def _get_lora() -> LoRASemanticAdapter:
    global _lora_adapter
    if _lora_adapter is None:
        _lora_adapter = LoRASemanticAdapter(_get_db(), rank=8, alpha=0.5)
    return _lora_adapter


def _get_cross() -> CrossSiteAnalyzer:
    global _cross_analyzer
    if _cross_analyzer is None:
        _cross_analyzer = CrossSiteAnalyzer(_get_db(), min_sites=2)
    return _cross_analyzer


@router.get("/graph/{site_id}")
async def get_semantic_graph(site_id: str):
    db = _get_db()
    graph = await db.get_graph(site_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Graph not found for site")
    return graph.to_dict()


@router.post("/context")
async def get_semantic_context(req: ContextRequest):
    db = _get_db()
    context = await db.get_graph_context(req.site_id, req.query)
    return context


@router.get("/similar/{site_id}")
async def find_similar_sites(site_id: str, limit: int = Query(5, ge=1, le=20)):
    db = _get_db()
    results = await db.find_similar_sites(site_id, limit=limit)
    return [{"site_id": sid, "similarity": score} for sid, score in results]


@router.post("/adapt")
async def apply_lora_adapter(req: AdaptRequest):
    lora = _get_lora()
    ctx = await lora.adapt(req.site_id, req.query)
    return ctx.to_dict()


@router.get("/patterns")
async def get_patterns(limit: int = Query(10, ge=1, le=50)):
    cross = _get_cross()
    patterns = await cross.find_patterns(limit=limit)
    return [p.to_dict() for p in patterns]


@router.get("/patterns/{site_id}")
async def get_site_patterns(site_id: str):
    cross = _get_cross()
    patterns = await cross.get_insights_for_site(site_id)
    return [p.to_dict() for p in patterns]


@router.get("/health")
async def semantic_health():
    db = _get_db()
    lora = _get_lora()
    cross = _get_cross()
    site_count = len(await db.get_all_site_ids())
    return {
        "status": "healthy",
        "semantic_db": {"status": "connected", "sites": site_count, "dimension": db.dimension},
        "lora_adapter": {"status": "ready", "rank": lora.rank, "alpha": lora.alpha},
        "cross_site_analyzer": {"status": "initialized", "min_sites": cross.min_sites},
    }
