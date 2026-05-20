import os
import logging

from fastapi import FastAPI, Depends
from pydantic import BaseModel

from app.auth import verify_api_key, set_api_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ZenSEO ML Service", version="1.0.0")

_api_key = os.environ.get("ML_API_KEY", "")
if _api_key:
    set_api_key(_api_key)
    logger.info("ML API key authentication enabled")
else:
    logger.warning("ML_API_KEY not set — authentication disabled")


class TrainRequest(BaseModel):
    states: list[dict] = []
    actions: list[dict] = []
    rewards: list[float] = []
    logprobs: list[dict] | None = None


class RecommendRequest(BaseModel):
    state: dict
    top_k: int = 3


class AdaptRequest(BaseModel):
    site_id: str
    query: str
    site_vector: list[float] | None = None


class TrainStepRequest(BaseModel):
    site_id: str
    query: str
    reward: float
    site_vector: list[float] | None = None
    lr: float = 1e-3


class EmbedRequest(BaseModel):
    texts: list[str]


class ClusterRequest(BaseModel):
    vectors: list[list[float]]
    site_ids: list[str]


class SharedEntitiesRequest(BaseModel):
    cluster: list[str]
    site_entities: dict[str, list[dict]]


trainer_loaded = False
lora_loaded = False
cross_site_loaded = False
embeddings_loaded = False
_loaded_warnings: list[str] = []


def _load_modules():
    global trainer_loaded, lora_loaded, cross_site_loaded, embeddings_loaded, _loaded_warnings
    if any([trainer_loaded, lora_loaded, cross_site_loaded, embeddings_loaded]):
        return

    from app import trainer as t
    from app import embeddings as e
    from app import lora as l
    from app import cross_site as c

    app.state.trainer = t.PPOTrainer()
    model_path = os.path.join(os.path.dirname(__file__), "..", "data", "ppo_model.pt")
    if os.path.exists(model_path):
        try:
            app.state.trainer.load(model_path)
            logger.info("PPO model loaded (step=%d)", app.state.trainer._train_step)
        except Exception as ex:
            _loaded_warnings.append(f"Failed to load PPO model: {ex}")
    global trainer_loaded
    trainer_loaded = True

    try:
        app.state.embed_fn = e.embed_text
        app.state.cosine_sim = e.cosine_similarity
        global embeddings_loaded
        embeddings_loaded = True
    except Exception as ex:
        _loaded_warnings.append(f"Embeddings unavailable: {ex}")

    try:
        app.state.lora = l.LoRASemanticAdapter(
            embed_fn=app.state.embed_fn if embeddings_loaded else None,
            cosine_fn=app.state.cosine_sim if embeddings_loaded else None,
        )
        global lora_loaded
        lora_loaded = True
    except Exception as ex:
        _loaded_warnings.append(f"LoRA unavailable: {ex}")

    try:
        app.state.cross_site = c.CrossSiteAnalyzer(
            embed_fn=app.state.embed_fn if embeddings_loaded else None,
            cosine_fn=app.state.cosine_sim if embeddings_loaded else None,
        )
        global cross_site_loaded
        cross_site_loaded = True
    except Exception as ex:
        _loaded_warnings.append(f"Cross-site analysis unavailable: {ex}")

    logger.info("ML modules loaded: trainer=%s lora=%s cross_site=%s embeddings=%s",
                trainer_loaded, lora_loaded, cross_site_loaded, embeddings_loaded)


@app.on_event("startup")
async def startup():
    try:
        _load_modules()
    except Exception as e:
        logger.error("Failed to load ML modules: %s", e)


@app.get("/v1/ml/health")
async def health(auth: str = Depends(verify_api_key)):
    return {
        "status": "ok" if any([trainer_loaded, lora_loaded, cross_site_loaded]) else "degraded",
        "trainer": trainer_loaded,
        "lora": lora_loaded,
        "cross_site": cross_site_loaded,
        "embeddings": embeddings_loaded,
        "warnings": _loaded_warnings,
    }


@app.get("/v1/ml/status")
async def status(auth: str = Depends(verify_api_key)):
    t = getattr(app.state, "trainer", None)
    return {
        "train_step": t._train_step if t else 0,
        "action_registry": t._action_registry if t else {},
        "trainer_loaded": trainer_loaded,
        "lora_loaded": lora_loaded,
        "cross_site_loaded": cross_site_loaded,
    }


@app.post("/v1/ml/train")
async def train(req: TrainRequest, auth: str = Depends(verify_api_key)):
    if not trainer_loaded:
        return {"status": "unavailable", "error": "Trainer not loaded"}
    from app.trainer import Trajectory
    traj = Trajectory(
        states=req.states,
        actions=req.actions,
        rewards=req.rewards,
        logprobs=req.logprobs,
    )
    stats = await app.state.trainer.update_policy([traj])
    return {"status": "ok", "stats": stats, "train_step": app.state.trainer._train_step}


@app.post("/v1/ml/recommend")
async def recommend(req: RecommendRequest, auth: str = Depends(verify_api_key)):
    if not trainer_loaded:
        return {"status": "unavailable", "error": "Trainer not loaded"}
    state_tensor = app.state.trainer._state_to_tensor(req.state).unsqueeze(0)
    import torch
    with torch.no_grad():
        dist = app.state.trainer._policy(state_tensor)
        action_probs = dist.probs.squeeze(0)
    top_probs, top_indices = action_probs.topk(req.top_k)
    action_reverse = {v: k for k, v in app.state.trainer._action_registry.items()}
    recommendations = []
    for prob, idx in zip(top_probs.tolist(), top_indices.tolist()):
        action_type = action_reverse.get(idx, f"action_{idx}")
        recommendations.append({"action_type": action_type, "confidence": round(prob, 4), "action_index": idx})
    return {"recommendations": recommendations, "train_step": app.state.trainer._train_step}


@app.post("/v1/ml/adapt")
async def adapt(req: AdaptRequest, auth: str = Depends(verify_api_key)):
    if not lora_loaded:
        return {"value": None, "error": "LoRA not loaded"}
    result = await app.state.lora.adapt(req.site_id, req.query, site_vector=req.site_vector)
    return {"value": result.to_dict() if hasattr(result, 'to_dict') else str(result)}


@app.post("/v1/ml/lora/train-step")
async def lora_train_step(req: TrainStepRequest, auth: str = Depends(verify_api_key)):
    if not lora_loaded:
        return {"error": "LoRA not loaded"}
    result = await app.state.lora.train_step(req.site_id, req.query, req.reward, site_vector=req.site_vector, lr=req.lr)
    return result


@app.post("/v1/ml/embed")
async def embed(req: EmbedRequest, auth: str = Depends(verify_api_key)):
    if not embeddings_loaded:
        return {"embeddings": [], "error": "Embeddings not loaded"}
    results = [app.state.embed_fn(t) for t in req.texts]
    return {"embeddings": results}


@app.post("/v1/ml/cluster")
async def cluster(req: ClusterRequest, auth: str = Depends(verify_api_key)):
    if not cross_site_loaded:
        return {"clusters": [], "error": "Cross-site analysis not loaded"}
    clusters = app.state.cross_site.cluster_vectors(req.vectors, req.site_ids)
    return {"clusters": clusters}


@app.post("/v1/ml/shared-entities")
async def shared_entities(req: SharedEntitiesRequest, auth: str = Depends(verify_api_key)):
    if not cross_site_loaded:
        return {"patterns": [], "error": "Cross-site analysis not loaded"}
    patterns = app.state.cross_site.find_shared_entities(req.cluster, req.site_entities)
    return {"patterns": patterns}
