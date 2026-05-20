from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from sqlalchemy.orm import Session
from uuid import uuid4
import secrets
import hashlib

from app.core.database import get_db
from app.core.db_models import APIKey
from app.core.auth import get_current_admin

router = APIRouter()


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


@router.get("")
async def list_api_keys(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    query = db.query(APIKey)
    
    if user_id:
        query = query.filter(APIKey.user_id == user_id)
    if is_active is not None:
        query = query.filter(APIKey.is_active == is_active)
    
    total = query.count()
    keys = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "data": [
            {
                "id": k.id,
                "label": k.label,
                "userId": k.user_id,
                "keyPrefix": k.key_prefix,
                "rateLimit": k.rate_limit,
                "callsCount": k.calls_count,
                "lastUsed": k.last_used_at.isoformat() if k.last_used_at else None,
                "created": k.created_at.strftime("%Y-%m-%d") if k.created_at else None,
                "expires": k.expires_at.strftime("%Y-%m-%d") if k.expires_at else None,
                "isActive": k.is_active,
            }
            for k in keys
        ],
        "meta": {"total": total, "page": page, "limit": limit},
    }


@router.get("/{key_id}")
async def get_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")
    
    return {
        "id": key.id,
        "label": key.label,
        "userId": key.user_id,
        "keyPrefix": key.key_prefix,
        "rateLimit": key.rate_limit,
        "callsCount": key.calls_count,
        "lastUsed": key.last_used_at.isoformat() if key.last_used_at else None,
        "created": key.created_at.strftime("%Y-%m-%d") if key.created_at else None,
        "expires": key.expires_at.strftime("%Y-%m-%d") if key.expires_at else None,
        "isActive": key.is_active,
    }


@router.post("")
async def create_api_key(
    data: dict,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    key_value = "zenseo_sk_" + secrets.token_hex(20)
    key_prefix = key_value[:20]
    key_hash_value = hash_key(key_value)
    
    user_id = data.get("user_id") or data.get("userId")
    if not user_id:
        raise HTTPException(status_code=422, detail="userId is required")
    new_key = APIKey(
        label=data.get("label", "New Key"),
        user_id=user_id,
        key_prefix=key_prefix,
        key_hash=key_hash_value,
        rate_limit=data.get("rate_limit") or data.get("rateLimit", 1000),
        is_active=True,
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    
    return {
        "apiKey": key_value,
        "apiKeyId": new_key.id,
    }


@router.put("/{key_id}")
async def update_api_key(
    key_id: str,
    data: dict,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")
    if data.get("label"):
        key.label = data["label"]
    if data.get("rate_limit") is not None:
        key.rate_limit = data["rate_limit"]
    elif data.get("rateLimit") is not None:
        key.rate_limit = data["rateLimit"]
    if data.get("is_active") is not None:
        key.is_active = data["is_active"]
    db.commit()
    db.refresh(key)
    return {"message": "API Key updated"}


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")
    
    key.is_active = False
    db.commit()
    
    return {"message": "API Key revoked"}