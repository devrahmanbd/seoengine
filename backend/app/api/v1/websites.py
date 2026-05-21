from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.database import get_db
from app.core.db_models import Website
from app.core.auth import get_current_admin

router = APIRouter()

class CreateWebsiteRequest(BaseModel):
    model_config = {"populate_by_name": True}

    user_id: str = Field(..., alias="userId", max_length=255)
    url: Optional[str] = Field(None, max_length=2048)
    name: Optional[str] = Field(None, max_length=255)
    platform: Optional[str] = Field("wordpress")
    status: Optional[str] = Field("connected")

class UpdateWebsiteRequest(BaseModel):
    model_config = {"populate_by_name": True}

    user_id: Optional[str] = Field(None, alias="userId", max_length=255)
    url: Optional[str] = Field(None, max_length=2048)
    name: Optional[str] = Field(None, max_length=255)
    platform: Optional[str] = Field(None)
    status: Optional[str] = Field(None)


@router.get("")
async def list_websites(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    platform: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    query = db.query(Website)
    
    if user_id:
        query = query.filter(Website.user_id == user_id)
    if status:
        query = query.filter(Website.status == status)
    if platform:
        query = query.filter(Website.platform == platform)
    if search:
        query = query.filter(
            (Website.name.ilike(f"%{search}%")) | 
            (Website.url.ilike(f"%{search}%"))
        )
    
    total = query.count()
    sites = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "url": s.url,
                "userId": s.user_id,
                "platform": s.platform,
                "status": s.status,
                "seoScore": s.seo_score or 0,
                "lastScan": s.last_scan_at.isoformat() if s.last_scan_at else None,
            }
            for s in sites
        ],
        "meta": {"total": total, "page": page, "limit": limit},
    }


@router.get("/{website_id}")
async def get_website(
    website_id: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    site = db.query(Website).filter(Website.id == website_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")
    
    return {
        "id": site.id,
        "name": site.name,
        "url": site.url,
        "userId": site.user_id,
        "platform": site.platform,
        "status": site.status,
        "seoScore": site.seo_score or 0,
        "lastScan": site.last_scan_at.isoformat() if site.last_scan_at else None,
    }


@router.post("")
async def create_website(
    data: CreateWebsiteRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    site = Website(
        user_id=data.user_id,
        url=data.url,
        name=data.name or data.url or "New Website",
        platform=data.platform,
        status=data.status,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return {
        "id": site.id,
        "name": site.name,
        "url": site.url,
        "userId": site.user_id,
        "platform": site.platform,
        "status": site.status,
    }


@router.put("/{website_id}")
async def update_website(
    website_id: str,
    data: UpdateWebsiteRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    site = db.query(Website).filter(Website.id == website_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")
    if data.name:
        site.name = data.name
    if data.url:
        site.url = data.url
    if data.platform:
        site.platform = data.platform
    if data.status is not None:
        site.status = data.status
    if data.user_id:
        site.user_id = data.user_id
    db.commit()
    db.refresh(site)
    return {
        "id": site.id,
        "name": site.name,
        "url": site.url,
        "userId": site.user_id,
        "platform": site.platform,
        "status": site.status,
    }


@router.delete("/{website_id}")
async def delete_website(
    website_id: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    site = db.query(Website).filter(Website.id == website_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")
    
    db.delete(site)
    db.commit()
    
    return {"message": "Website disconnected"}


@router.post("/{website_id}/scan")
async def trigger_scan(
    website_id: str,
    data: dict,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    site = db.query(Website).filter(Website.id == website_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")
    
    return {
        "taskId": str(uuid4()),
        "message": "Scan initiated",
    }