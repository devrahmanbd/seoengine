import logging
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel

from app.core.auth import get_current_admin
from app.core.db_models import Admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/v1/ml", tags=["ML Service"])


class ToggleRequest(BaseModel):
    enabled: bool


def _get_ml_client(request: Request):
    ml = getattr(request.app.state, "ml_client", None)
    if not ml:
        raise HTTPException(status_code=503, detail="ML client not initialized")
    return ml


@router.get("/status")
async def ml_status(
    request: Request,
    current_admin: Admin = Depends(get_current_admin),
):
    ml = _get_ml_client(request)
    return await ml.get_status()


@router.post("/toggle")
async def ml_toggle(
    request: Request,
    req: ToggleRequest,
    current_admin: Admin = Depends(get_current_admin),
):
    ml = _get_ml_client(request)
    await ml.toggle(req.enabled)
    return {"enabled": req.enabled, "status": "ok"}


@router.get("/container/status")
async def container_status(
    current_admin: Admin = Depends(get_current_admin),
):
    try:
        from app.services.docker_manager import get_container_status, is_docker_available
        if not is_docker_available():
            return {"available": False, "error": "Docker not installed on host"}
        return get_container_status()
    except Exception as e:
        logger.warning("Docker status check failed: %s", e)
        return {"available": False, "error": str(e)}


@router.post("/container/start")
async def container_start(
    current_admin: Admin = Depends(get_current_admin),
):
    try:
        from app.services.docker_manager import start_container
        return start_container()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/container/stop")
async def container_stop(
    current_admin: Admin = Depends(get_current_admin),
):
    try:
        from app.services.docker_manager import stop_container
        return stop_container()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/container/restart")
async def container_restart(
    current_admin: Admin = Depends(get_current_admin),
):
    try:
        from app.services.docker_manager import restart_container
        return restart_container()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/container/logs")
async def container_logs(
    tail: int = Query(50, ge=10, le=500),
    current_admin: Admin = Depends(get_current_admin),
):
    try:
        from app.services.docker_manager import get_container_logs
        return get_container_logs(tail=tail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
