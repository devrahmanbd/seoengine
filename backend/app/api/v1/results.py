from fastapi import APIRouter, Query, Depends
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.db_models import Website, SEOResult
from app.core.auth import get_current_admin

router = APIRouter()


@router.get("/summary")
async def get_results_summary(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    total_websites = db.query(Website).count()
    
    results = db.query(SEOResult).all()
    avg_score = 0
    if results:
        avg_score = sum(r.score for r in results if r.score) / len(results)
    
    all_issues = []
    for r in results:
        if r.issues:
            all_issues.extend(r.issues)
    
    issues_by_type = {"error": 0, "warning": 0, "info": 0}
    for issue in all_issues:
        severity = issue.get("severity", "info")
        if severity in issues_by_type:
            issues_by_type[severity] += 1
    
    return {
        "totalWebsites": total_websites,
        "avgSeoScore": round(avg_score),
        "totalIssues": len(all_issues),
        "issuesByType": issues_by_type,
        "topPerformers": [],
        "needsAttention": [],
    }


@router.get("")
async def list_results(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    result_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    query = db.query(SEOResult)
    
    if result_type:
        query = query.filter(SEOResult.result_type == result_type)
    
    total = query.count()
    results = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "data": [
            {
                "id": r.id,
                "websiteId": r.website_id,
                "resultType": r.result_type,
                "seoScore": r.score or 0,
                "status": "completed" if r.score else "pending",
                "createdAt": r.scanned_at.isoformat() if r.scanned_at else None,
            }
            for r in results
        ],
        "meta": {"total": total, "page": page, "limit": limit},
    }


@router.get("/issues")
async def get_issues(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    severity: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    query = db.query(SEOResult).filter(SEOResult.issues != None)
    
    total = query.count()
    results = query.offset((page - 1) * limit).limit(limit).all()
    
    all_issues = []
    for r in results:
        if r.issues:
            for issue in r.issues:
                issue["websiteId"] = r.website_id
                issue["resultId"] = r.id
                all_issues.append(issue)
    
    if severity:
        all_issues = [i for i in all_issues if i.get("severity") == severity]
    if category:
        all_issues = [i for i in all_issues if i.get("category") == category]
    
    return {
        "data": all_issues[:limit],
        "meta": {"total": len(all_issues), "page": page, "limit": limit},
    }