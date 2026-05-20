from fastapi import APIRouter, Query, Depends
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.db_models import AgentLog
from app.core.auth import get_current_admin

router = APIRouter()


@router.get("")
async def list_ai_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    query = db.query(AgentLog)
    
    if agent_type:
        query = query.filter(AgentLog.agent_type == agent_type)
    if status:
        query = query.filter(AgentLog.status == status)
    
    total = query.count()
    logs = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "data": [
            {
                "id": log.id,
                "agentType": log.agent_type,
                "taskId": log.task_id,
                "status": log.status,
                "input": log.input_data.get("input", "") if log.input_data else "",
                "output": log.output_data.get("output", "") if log.output_data else "",
                "duration": f"{log.execution_time_ms}ms" if log.execution_time_ms else "0ms",
                "timestamp": log.created_at.strftime("%H:%M:%S") if log.created_at else "-",
            }
            for log in logs
        ],
        "meta": {"total": total, "page": page, "limit": limit},
    }


@router.get("/stats")
async def get_ai_stats(db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    return {
        "totalRuns24h": 0,
        "successRate": 0,
        "avgExecutionTime": 0,
        "activeAgents": 0,
    }


@router.get("/agents")
async def get_agents(db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    return []