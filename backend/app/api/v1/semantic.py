from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/semantic", tags=["semantic"])


class ContextRequest(BaseModel):
    site_id: str
    query: str


class AdaptRequest(BaseModel):
    site_id: str
    query: str


def _get_db():
    from app.services.semantic.db import SemanticDB
    if not hasattr(_get_db, "_instance"):
        _get_db._instance = SemanticDB(dimension=32)
    return _get_db._instance


def _get_ml(request: Request):
    return getattr(request.app.state, "ml_client", None)


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
async def apply_lora_adapter(req: AdaptRequest, request: Request):
    ml = _get_ml(request)
    if ml and ml.enabled:
        result = await ml.adapt(req.site_id, req.query)
        if result:
            return result
    raise HTTPException(status_code=503, detail="ML service not available for LoRA adaptation")


@router.get("/patterns")
async def get_patterns(limit: int = Query(10, ge=1, le=50), request: Request = None):
    if request:
        ml = _get_ml(request)
        if ml and ml.enabled:
            from app.core.database import get_db as db_session
            db = _get_db()
            site_ids = await db.get_all_site_ids()
            vectors = []
            valid_ids = []
            for sid in site_ids:
                vec = await db.get_topic_vector(sid)
                if vec:
                    vectors.append(vec)
                    valid_ids.append(sid)
            if vectors:
                clusters = await ml.cluster_vectors(vectors, valid_ids)
                if clusters:
                    result = []
                    for cluster in clusters:
                        site_entities = {}
                        for sid in cluster:
                            graph = await db.get_graph(sid)
                            if graph:
                                site_entities[sid] = [
                                    {
                                        "id": n.id,
                                        "label": n.label,
                                        "type": n.type,
                                        "embedding": n.embedding or [],
                                    }
                                    for n in graph.nodes
                                    if n.embedding
                                ]
                        patterns = await ml.find_shared_entities(cluster, site_entities)
                        result.extend(patterns)
                    return result[:limit]
    return []


@router.get("/patterns/{site_id}")
async def get_site_patterns(site_id: str, request: Request = None):
    patterns = await get_patterns(limit=50, request=request)
    site_patterns = [p for p in patterns if any(e in str(p) for e in [site_id])]
    return site_patterns[:10]


@router.get("/health")
async def semantic_health(request: Request = None):
    db = _get_db()
    site_count = len(await db.get_all_site_ids())
    ml = _get_ml(request) if request else None
    ml_status = "connected" if ml and ml.enabled else "unavailable"
    return {
        "status": "healthy",
        "semantic_db": {"status": "connected", "sites": site_count, "dimension": db.dimension},
        "ml_service": {"status": ml_status},
    }
