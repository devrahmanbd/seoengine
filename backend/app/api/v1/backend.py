from fastapi import APIRouter, Query, Depends
from typing import Optional
from sqlalchemy.orm import Session
import time

from app.core.database import get_db
from app.core.db_models import ErrorLog, Task
from app.core.auth import get_current_admin

router = APIRouter()


@router.get("/backend/status")
async def get_backend_status(db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    return {
        "api": {"status": "online", "uptime": "0s", "version": "1.0.0"},
        "database": {"status": "connected", "latency": 0},
        "redis": {"status": "connected"},
        "agents": {"active": 0, "idle": 0},
    }


@router.get("/backend/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": f"{time.time()}",
    }


@router.get("/logs/errors")
async def get_error_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    level: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    query = db.query(ErrorLog)
    
    if level:
        query = query.filter(ErrorLog.level == level)
    if source:
        query = query.filter(ErrorLog.source == source)
    
    total = query.count()
    logs = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "data": [
            {
                "id": log.id,
                "timestamp": log.created_at.strftime("%H:%M:%S") if log.created_at else "-",
                "level": log.level,
                "source": log.source,
                "message": log.message,
            }
            for log in logs
        ],
        "meta": {"total": total, "page": page, "limit": limit},
    }


@router.get("/tasks")
async def get_tasks(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    query = db.query(Task)
    
    if status:
        query = query.filter(Task.status == status)
    
    total = query.count()
    tasks = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "data": [
            {
                "id": task.id,
                "type": task.task_type,
                "website": task.website_id if task.website_id else "-",
                "status": task.status,
                "started": task.started_at.strftime("%H:%M") if task.started_at else "-",
                "duration": str(task.completed_at - task.started_at) if task.started_at and task.completed_at else "-",
            }
            for task in tasks
        ],
        "meta": {"total": total, "page": page, "limit": limit},
    }