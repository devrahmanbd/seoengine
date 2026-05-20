"""
Google Search Console API Integration
OAuth-based integration for real Search Console data
"""

import os
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json


class SearchConsoleAPI:
    """Google Search Console API client"""
    
    def __init__(self, access_token: str = None):
        self.access_token = access_token or os.getenv("GSC_ACCESS_TOKEN", "")
        self.site_url = os.getenv("GSC_SITE_URL", "")
        self.base_url = "https://searchconsole.googleapis.com/v1"
    
    async def _request(self, endpoint: str, method: str = "GET", 
                       params: Dict = None, body: Dict = None) -> Dict:
        """Make authenticated request to Search Console API"""
        
        if not self.access_token:
            return {"error": "GSC access token required", "needs_oauth": True}
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with aiohttp.ClientTimeout(total=30) as timeout:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    if method == "GET":
                        async with session.get(url, params=params, 
                                              headers=headers) as response:
                            return await response.json()
                    else:
                        async with session.post(url, json=body, 
                                               headers=headers) as response:
                            return await response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def search_analytics(self, start_date: str = None, end_date: str = None,
                               dimensions: List[str] = None) -> Dict[str, Any]:
        """Get search analytics data"""
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        dimensions = dimensions or ["query", "page", "country", "device"]
        
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": dimensions,
            "rowLimit": 25000
        }
        
        if self.site_url:
            endpoint = f"/sites/{self.site_url}/searchAnalytics/query"
        else:
            endpoint = "/sites/searchAnalytics/query"
        
        return await self._request(endpoint, method="POST", body=body)
    
    async def get_top_queries(self, days: int = 28, limit: int = 100) -> List[Dict]:
        """Get top performing queries"""
        
        result = await self.search_analytics(
            start_date=(datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d"),
            dimensions=["query"]
        )
        
        rows = result.get("rows", [])
        queries = []
        
        for row in rows[:limit]:
            queries.append({
                "query": row["keys"][0],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": row.get("ctr", 0),
                "position": row.get("position", 0)
            })
        
        return queries
    
    async def get_top_pages(self, days: int = 28, limit: int = 50) -> List[Dict]:
        """Get top performing pages"""
        
        result = await self.search_analytics(
            start_date=(datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d"),
            dimensions=["page"]
        )
        
        rows = result.get("rows", [])
        pages = []
        
        for row in rows[:limit]:
            pages.append({
                "page": row["keys"][0],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": row.get("ctr", 0),
                "position": row.get("position", 0)
            })
        
        return pages
    
    async def get_sitemap_status(self) -> Dict[str, Any]:
        """Get sitemap submission status"""
        
        if not self.site_url:
            return {"error": "Site URL not configured"}
        
        endpoint = f"/sites/{self.site_url}/sitemaps"
        
        return await self._request(endpoint)
    
    async def get_index_status(self) -> Dict[str, Any]:
        """Get URL indexing status"""
        
        result = await self.search_analytics(
            dimensions=["page"]
        )
        
        total_pages = len(result.get("rows", []))
        total_impressions = sum(r.get("impressions", 0) for r in result.get("rows", []))
        
        return {
            "total_indexed_pages": total_pages,
            "total_impressions": total_impressions,
            "site_url": self.site_url
        }


class GSCService:
    """High-level Search Console operations"""
    
    def __init__(self, access_token: str = None, site_url: str = None):
        self.api = SearchConsoleAPI(access_token)
        if site_url:
            self.api.site_url = site_url
    
    async def get_performance_summary(self, days: int = 28) -> Dict[str, Any]:
        """Get performance summary for the site"""
        
        queries = await self.api.get_top_queries(days=days)
        
        total_clicks = sum(q["clicks"] for q in queries)
        total_impressions = sum(q["impressions"] for q in queries)
        avg_ctr = sum(q["ctr"] for q in queries) / len(queries) if queries else 0
        avg_position = sum(q["position"] for q in queries) / len(queries) if queries else 0
        
        return {
            "period_days": days,
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "average_ctr": round(avg_ctr * 100, 2),
            "average_position": round(avg_position, 1),
            "total_queries": len(queries),
            "top_queries": queries[:20]
        }
    
    async def get_ranking_opportunities(self, days: int = 28) -> List[Dict]:
        """Find ranking opportunities - queries on page 2-3"""
        
        queries = await self.api.get_top_queries(days=days)
        
        opportunities = []
        
        for q in queries:
            position = q["position"]
            if 10 < position <= 30 and q["clicks"] > 10:
                opportunities.append({
                    "query": q["query"],
                    "current_position": position,
                    "potential_clicks": q["clicks"] * 2,
                    "difficulty": "medium" if position <= 20 else "hard",
                    "action": "Optimize existing content" if position <= 25 else "Create new content"
                })
        
        return sorted(opportunities, key=lambda x: x["potential_clicks"], reverse=True)[:20]


# Singleton
_gsc_service = None

def get_gsc_service(access_token: str = None, site_url: str = None) -> GSCService:
    global _gsc_service
    if _gsc_service is None:
        _gsc_service = GSCService(access_token, site_url)
    return _gsc_service