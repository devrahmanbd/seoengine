import os
import logging

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db, engine, SessionLocal
from app.core.auth import get_current_admin
from app.core.client_auth import ClientOriginMiddleware
from app.api.v1 import users, websites, api_keys, results, backend, ai_logs, ml
from app.api.v1.auth import router as auth_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ZenSEO Admin API...")
    init_db()

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
