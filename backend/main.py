"""
ZenSEO AI - Admin API Server
FastAPI-based REST API for admin dashboard
"""

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db, engine, SessionLocal
from app.api.v1 import users, websites, api_keys, results, backend, ai_logs, repl, semantic
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

    # ------------------------------------------------------------------
    # INTEGRATION: Wire all learning / growth / executor components
    # ------------------------------------------------------------------
    app.state.components = {}

    # 1. ScoredDataBuffer singleton
    try:
        from app.services.atropos.scored_data_api import scored_data_buffer
        app.state.scored_data_buffer = scored_data_buffer
        app.state.components["scored_data_buffer"] = scored_data_buffer
        logger.info("ScoredDataBuffer initialized (size=%d)", len(scored_data_buffer))
    except Exception as e:
        logger.warning("Failed to init ScoredDataBuffer: %s", e)

    # 2. PPOTrainer (load existing model if available)
    try:
        from app.services.atropos.trainer import PPOTrainer
        trainer = PPOTrainer()
        model_path = os.path.join(os.path.dirname(__file__), "data", "ppo_model.pt")
        if os.path.exists(model_path):
            trainer.load(model_path)
            logger.info("PPO model loaded from %s (step=%d)", model_path, trainer._train_step)
        else:
            logger.info("No existing PPO model found, starting fresh")
        app.state.ppo_trainer = trainer
        app.state.components["ppo_trainer"] = trainer
    except Exception as e:
        logger.warning("Failed to init PPOTrainer: %s", e)

    # 3. DataCollector & RewardCalculator
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

    # 4. TrainingPipeline + auto-train
    try:
        from app.services.learning.training_pipeline import TrainingPipeline
        pipeline = TrainingPipeline(
            collector=app.state.components.get("data_collector"),
            trainer=app.state.components.get("ppo_trainer"),
            buffer=app.state.components.get("scored_data_buffer"),
        )
        await pipeline.start_auto_train(interval=3600)
        app.state.training_pipeline = pipeline
        app.state.components["training_pipeline"] = pipeline
        logger.info("TrainingPipeline started (auto-train every 3600s)")
    except Exception as e:
        logger.warning("Failed to init TrainingPipeline: %s", e)

    # 5. FeedbackLoop
    try:
        from app.services.learning.feedback_loop import FeedbackLoop
        feedback = FeedbackLoop(
            collector=app.state.components.get("data_collector"),
            calculator=app.state.components.get("reward_calculator"),
            pipeline=app.state.components.get("training_pipeline"),
        )
        app.state.feedback_loop = feedback
        app.state.components["feedback_loop"] = feedback
        logger.info("FeedbackLoop initialized")
    except Exception as e:
        logger.warning("Failed to init FeedbackLoop: %s", e)

    # 6. DecisionIntegrator
    try:
        from app.services.learning.decision_integrator import DecisionIntegrator
        integrator = DecisionIntegrator(
            trainer=app.state.components.get("ppo_trainer"),
            buffer=app.state.components.get("scored_data_buffer"),
        )
        app.state.decision_integrator = integrator
        app.state.components["decision_integrator"] = integrator
        logger.info("DecisionIntegrator initialized")
    except Exception as e:
        logger.warning("Failed to init DecisionIntegrator: %s", e)

    # 7. GrowthScorer
    try:
        from app.services.learning.growth_scorer import GrowthScorer
        scorer = GrowthScorer(collector=app.state.components.get("data_collector"))
        app.state.growth_scorer = scorer
        app.state.components["growth_scorer"] = scorer
        logger.info("GrowthScorer initialized")
    except Exception as e:
        logger.warning("Failed to init GrowthScorer: %s", e)

    # 8. OpportunityDetector & ActionScheduler
    try:
        from app.services.growth.opportunity_detector import OpportunityDetector
        from app.services.growth.action_scheduler import ActionScheduler
        detector = OpportunityDetector(
            decision_integrator=app.state.components.get("decision_integrator"),
        )
        scheduler = ActionScheduler()
        app.state.opportunity_detector = detector
        app.state.action_scheduler = scheduler
        app.state.components["opportunity_detector"] = detector
        app.state.components["action_scheduler"] = scheduler
        logger.info("OpportunityDetector / ActionScheduler initialized")
    except Exception as e:
        logger.warning("Failed to init OpportunityDetector/ActionScheduler: %s", e)

    # 9. SafetyMonitor, ActionExecutor, DecisionExecutor
    try:
        from app.services.executor.safety_monitor import SafetyMonitor
        from app.services.executor.action_executor import ActionExecutor
        from app.services.executor.decision_executor import DecisionExecutor
        safety = SafetyMonitor()
        action_exec = ActionExecutor()
        decision_exec = DecisionExecutor(
            action_executor=action_exec,
            safety_monitor=safety,
        )
        app.state.safety_monitor = safety
        app.state.action_executor = action_exec
        app.state.decision_executor = decision_exec
        app.state.components["safety_monitor"] = safety
        app.state.components["action_executor"] = action_exec
        app.state.components["decision_executor"] = decision_exec
        logger.info("SafetyMonitor / ActionExecutor / DecisionExecutor initialized")
    except Exception as e:
        logger.warning("Failed to init executor components: %s", e)

    # 10. Register all 6 environments in Registry
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

    # 11. System verification
    try:
        from app.core.startup import verify_system
        warnings = await verify_system(dict(app.state.components))
        if warnings:
            logger.warning("System verification completed with %d warnings", len(warnings))
            for w in warnings:
                logger.warning("  - %s", w)
        app.state.components["verification_warnings"] = warnings
    except Exception as e:
        logger.warning("System verification failed: %s", e)

    logger.info("ZenSEO Admin API startup complete — %d components initialized", len(app.state.components))
    yield

    # ------------------------------------------------------------------
    # SHUTDOWN
    # ------------------------------------------------------------------
    logger.info("Shutting down ZenSEO Admin API...")

    # 1. Stop auto-train
    try:
        pipeline = getattr(app.state, "training_pipeline", None)
        if pipeline:
            await pipeline.stop_auto_train()
            logger.info("Auto-train stopped")
    except Exception as e:
        logger.warning("Error stopping auto-train: %s", e)

    # 2. Save PPO model
    try:
        trainer = getattr(app.state, "ppo_trainer", None)
        if trainer:
            model_path = os.path.join(os.path.dirname(__file__), "data", "ppo_model.pt")
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            trainer.save(model_path)
            logger.info("PPO model saved to %s (step=%d)", model_path, trainer._train_step)
    except Exception as e:
        logger.warning("Error saving PPO model: %s", e)

    # 3. Persist sessions
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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/admin/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/admin/v1/users", tags=["Users"])
app.include_router(websites.router, prefix="/api/admin/v1/websites", tags=["Websites"])
app.include_router(api_keys.router, prefix="/api/admin/v1/api-keys", tags=["API Keys"])
app.include_router(results.router, prefix="/api/admin/v1/results", tags=["Results"])
app.include_router(backend.router, prefix="/api/admin/v1", tags=["Backend"])
app.include_router(ai_logs.router, prefix="/api/admin/v1/ai-logs", tags=["AI Logs"])

# V1 API routers (Hermes REPL, Semantic DB, Atropos)
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
async def policy_recommend(website_id: str = "", top_k: int = 3):
    from fastapi import HTTPException
    integrator = getattr(app.state, "decision_integrator", None)
    if integrator is None:
        raise HTTPException(status_code=503, detail="DecisionIntegrator not available")
    state = {"website_id": website_id, "score": 0, "issues": 0}
    recs = await integrator.recommend_actions(state, top_k=top_k)
    return {"website_id": website_id, "recommendations": recs}


@app.get("/v1/growth/score")
async def growth_score(website_id: str = ""):
    from fastapi import HTTPException
    scorer = getattr(app.state, "growth_scorer", None)
    if scorer is None:
        raise HTTPException(status_code=503, detail="GrowthScorer not available")
    score = await scorer.score_growth(website_id)
    return score


@app.get("/v1/policy/info")
async def policy_info():
    from app.services.learning.policy_server import PolicyServer
    server = PolicyServer(
        trainer=getattr(app.state, "ppo_trainer", None),
        integrator=getattr(app.state, "decision_integrator", None),
    )
    return await server.get_policy_info()


@app.get("/v1/components")
async def list_components():
    return {
        "components": list(getattr(app.state, "components", {}).keys()),
        "count": len(getattr(app.state, "components", {})),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
