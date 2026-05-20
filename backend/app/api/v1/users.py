from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.db_models import User
from app.core.auth import get_current_admin
from app.core.auth import get_password_hash

router = APIRouter()


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    plan: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    query = db.query(User)
    
    if search:
        query = query.filter(
            (User.name.ilike(f"%{search}%")) | 
            (User.email.ilike(f"%{search}%"))
        )
    if plan:
        query = query.filter(User.plan == plan)
    if status:
        query = query.filter(User.subscription_status == status)
    
    total = query.count()
    users = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "data": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "plan": u.plan,
                "subscriptionStatus": u.subscription_status,
                "apiCallsUsed": u.api_calls_used,
                "apiCallsLimit": u.api_calls_limit,
                "websitesCount": len(u.websites) if u.websites else 0,
                "createdAt": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit if total > 0 else 0,
        },
    }


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "plan": user.plan,
        "subscriptionStatus": user.subscription_status,
        "apiCallsUsed": user.api_calls_used,
        "apiCallsLimit": user.api_calls_limit,
        "websitesCount": len(user.websites) if user.websites else 0,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("")
async def create_user(
    data: dict,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    existing = db.query(User).filter(User.email == data.get("email")).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    user = User(
        email=data.get("email"),
        name=data.get("name"),
        password_hash=get_password_hash(data.get("password", "password")),
        plan=data.get("plan", "free"),
        subscription_status=data.get("subscription_status", "active"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "plan": user.plan,
        "subscriptionStatus": user.subscription_status,
    }


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    data: dict,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if data.get("email"):
        user.email = data["email"]
    if data.get("name"):
        user.name = data["name"]
    if data.get("plan"):
        user.plan = data["plan"]
    if data.get("subscription_status"):
        user.subscription_status = data["subscription_status"]
    
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "plan": user.plan,
        "subscriptionStatus": user.subscription_status,
    }


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted"}