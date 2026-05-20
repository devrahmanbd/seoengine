import os
import logging

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db, engine, SessionLocal
from app.core.auth import get_current_admin
from app.core.client_auth import ClientOriginMiddleware
from app.api.v1 import users, websites, api_keys, results, backend, ai_logs, repl, semantic, ml
from app.api.v1.auth import router as auth_router
from app.api.v1.growth import router as growth_router
from app.api.v1.repl import startup_repl, shutdown_repl
from app.services.atropos.scored_data_api import ScoredDataAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ZenSEO Admin API...")
    init_db()
    await startup_repl()
    logger.info("Database initialized")

    app.state.components = {}
    app.state.ml_client = None

    try:
        from app.services.ml_client import MLClient
        client = MLClient()
        app.state.ml_client = client
        app.state.components["ml_client"] = client
        available = await client.is_available()
        logger.info("ML service %s", "AVAILABLE" if available else "OFFLINE/DISABLED")
    except Exception as e:
        logger.warning("Failed to init MLClient: %s", e)

    try:
        from app.services.learning.data_collector import DataCollector
        from app.services.learning.reward_calculator import RewardCalculator
        collector = DataCollector(db_session_factory=SessionLocal)
        calculator = RewardCalculator()
        app.state.data_collector = collector
        app.state.reward_calculator = calculator
        app.state.components["data_collector"] = collector
        app.state.components["reward_calculator"] = calculator
        logger.info("DataCollector / RewardCalculator initialized")
    except Exception as e:
        logger.warning("Failed to init DataCollector: %s", e)

    try:
        from app.services.learning.growth_scorer import GrowthScorer
        scorer = GrowthScorer(collector=app.state.components.get("data_collector"))
        app.state.growth_scorer = scorer
        app.state.components["growth_scorer"] = scorer
        logger.info("GrowthScorer initialized")
    except Exception as e:
        logger.warning("Failed to init GrowthScorer: %s", e)

    try:
        from app.services.growth.action_scheduler import ActionScheduler
        scheduler = ActionScheduler()
        app.state.action_scheduler = scheduler
        app.state.components["action_scheduler"] = scheduler
        logger.info("ActionScheduler initialized")
    except Exception as e:
        logger.warning("Failed to init ActionScheduler: %s", e)

    try:
        from app.services.atropos.base_env import Registry
        from app.services.executor.safety_monitor import SafetyMonitor
        from app.services.executor.action_executor import ActionExecutor
        from app.services.executor.decision_executor import DecisionExecutor
        from app.services.learning.decision_integrator import DecisionIntegrator
        from app.services.learning.feedback_loop import FeedbackLoop
        from app.services.growth.action_scheduler import ActionScheduler
        safety = SafetyMonitor()
        env_registry = Registry
        action_exec = ActionExecutor(env_registry=env_registry)
        integrator = DecisionIntegrator()
        scheduler = ActionScheduler()
        feedback = FeedbackLoop()
        decision_exec = DecisionExecutor(
            integrator=integrator,
            scheduler=scheduler,
            env_registry=env_registry,
            feedback_loop=feedback,
        )
        app.state.safety_monitor = safety
        app.state.action_executor = action_exec
        app.state.decision_executor = decision_exec
        app.state.components["safety_monitor"] = safety
        app.state.components["action_executor"] = action_exec
        app.state.components["decision_executor"] = decision_exec
        app.state.components["decision_integrator"] = integrator
        logger.info("SafetyMonitor / ActionExecutor / DecisionExecutor initialized")
    except Exception as e:
        logger.warning("Failed to init executor components: %s", e)
        import traceback
        logger.warning(traceback.format_exc())

    try:
        from app.services.atropos.base_env import Registry
        from app.services.atropos.environments import (
            TechnicalSEOEnv, ContentSEOEnv, KeywordResearchEnv,
            BacklinkEnv, CWVEnv, SchemaEnv,
        )
        Registry.register("technical_seo", TechnicalSEOEnv)
        Registry.register("content_seo", ContentSEOEnv)
        Registry.register("keyword_research", KeywordResearchEnv)
        Registry.register("backlink", BacklinkEnv)
        Registry.register("cwv", CWVEnv)
        Registry.register("schema", SchemaEnv)
        app.state.components["environments"] = list(Registry.list())
        logger.info("Registered %d environments: %s", len(Registry.list()), Registry.list())
    except Exception as e:
        logger.warning("Failed to register environments: %s", e)

    logger.info("ZenSEO Admin API startup complete — %d components initialized", len(app.state.components))
    yield

    logger.info("Shutting down ZenSEO Admin API...")

    try:
        ml = getattr(app.state, "ml_client", None)
        if ml:
            await ml.close()
            logger.info("ML client closed")
    except Exception as e:
        logger.warning("Error closing ML client: %s", e)

    try:
        await shutdown_repl()
        logger.info("REPL sessions persisted")
    except Exception as e:
        logger.warning("Error shutting down REPL: %s", e)

    logger.info("ZenSEO Admin API shutdown complete")


app = FastAPI(
    title="ZenSEO Admin API",
    description="Admin dashboard API for ZenSEO AI SaaS",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ClientOriginMiddleware)

app.include_router(auth_router, prefix="/api/admin/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/admin/v1/users", tags=["Users"])
app.include_router(websites.router, prefix="/api/admin/v1/websites", tags=["Websites"])
app.include_router(api_keys.router, prefix="/api/admin/v1/api-keys", tags=["API Keys"])
app.include_router(results.router, prefix="/api/admin/v1/results", tags=["Results"])
app.include_router(backend.router, prefix="/api/admin/v1", tags=["Backend"])
app.include_router(ai_logs.router, prefix="/api/admin/v1/ai-logs", tags=["AI Logs"])
app.include_router(ml.router)

app.include_router(repl.router, tags=["REPL"])
app.include_router(semantic.router)
app.include_router(growth_router)
app.include_router(ScoredDataAPI, tags=["Atropos"])


@app.get("/")
async def root():
    return {"status": "ok", "service": "ZenSEO Admin API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/v1/policy/recommend")
async def policy_recommend(website_id: str = "", top_k: int = 3, admin=Depends(get_current_admin)):
    from fastapi import HTTPException
    ml = getattr(app.state, "ml_client", None)
    if not ml or not ml.enabled:
        raise HTTPException(status_code=503, detail="ML service not available")
    state = {"website_id": website_id, "score": 0, "issues": 0}
    recs = await ml.recommend(state, top_k=top_k)
    return {"website_id": website_id, "recommendations": recs}


@app.get("/v1/growth/score")
async def growth_score(website_id: str = "", admin=Depends(get_current_admin)):
    from fastapi import HTTPException
    scorer = getattr(app.state, "growth_scorer", None)
    if scorer is None:
        raise HTTPException(status_code=503, detail="GrowthScorer not available")
    score = await scorer.score_growth(website_id)
    return score


@app.get("/v1/policy/info")
async def policy_info(admin=Depends(get_current_admin)):
    ml = getattr(app.state, "ml_client", None)
    if not ml or not ml.enabled:
        return {"available": False, "reason": "ML service not available"}
    return await ml.get_status()


@app.get("/v1/components")
async def list_components(admin=Depends(get_current_admin)):
    return {
        "components": list(getattr(app.state, "components", {}).keys()),
        "count": len(getattr(app.state, "components", {})),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.api_host, port=settings.api_port)
