"""
SEMrush API Integration
Real keyword research, competitor analysis, and domain analytics
"""

import os
import aiohttp
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime


class SEMrushAPI:
    """SEMrush API client for keyword and competitor data"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SEMRUSH_API_KEY", "")
        self.base_url = "https://api.semrush.com"
        
    async def _request(self, endpoint: str, params: Dict) -> Dict:
        """Make authenticated request to SEMrush API"""
        
        if not self.api_key:
            return {"error": "SEMrush API key required", "needs_api_key": True}
        
        params["key"] = self.api_key
        
        try:
            async with aiohttp.ClientTimeout(total=30) as timeout:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(f"{self.base_url}{endpoint}", 
                                          params=params) as response:
                        if response.status == 200:
                            text = await response.text()
                            return self._parse_csv(text)
                        elif response.status == 401:
                            return {"error": "Invalid API key"}
                        else:
                            return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_csv(self, text: str) -> Dict:
        """Parse CSV response from SEMrush"""
        lines = text.strip().split("\n")
        if len(lines) < 2:
            return {"error": "Invalid response"}
        
        headers = lines[0].split(";")
        data = []
        
        for line in lines[1:]:
            if line.strip():
                values = line.split(";")
                row = {headers[i]: values[i] if i < len(values) else "" 
                       for i in range(len(headers))}
                data.append(row)
        
        return {"success": True, "data": data, "count": len(data)}
    
    async def keyword_overview(self, keyword: str) -> Dict[str, Any]:
        """Get keyword overview data"""
        
        return await self._request("/?type=phrase_all", {
            "phrase": keyword,
            "database": "us",
            "display_limit": 10
        })
    
    async def keyword_difficulty(self, keyword: str) -> Dict[str, Any]:
        """Get keyword difficulty score"""
        
        return await self._request("/?type=phrase_kdi", {
            "phrase": keyword,
            "database": "us"
        })
    
    async def related_keywords(self, keyword: str, limit: int = 20) -> List[Dict]:
        """Find related keywords"""
        
        result = await self._request("/?type=phrase_related", {
            "phrase": keyword,
            "database": "us",
            "display_limit": limit
        })
        
        if "data" in result:
            return result["data"]
        return []
    
    async def domain_organic(self, domain: str, limit: int = 50) -> List[Dict]:
        """Get domain's organic keywords"""
        
        result = await self._request("/?type=domain_organic", {
            "domain": domain,
            "database": "us",
            "display_limit": limit
        })
        
        if "data" in result:
            return result["data"]
        return []
    
    async def domain_competitors(self, domain: str) -> List[Dict]:
        """Get domain's organic competitors"""
        
        result = await self._request("/?type=domain_organic_organic", {
            "domain": domain,
            "database": "us",
            "display_limit": 10
        })
        
        if "data" in result:
            return result["data"]
        return []
    
    async def domain_advertisers(self, domain: str) -> List[Dict]:
        """Get domain's paid (PPC) competitors"""
        
        result = await self._request("/?type=domain_advertisers", {
            "domain": domain,
            "database": "us",
            "display_limit": 10
        })
        
        if "data" in result:
            return result["data"]
        return []
    
    async def backlinks_overview(self, domain: str) -> Dict[str, Any]:
        """Get backlinks overview"""
        
        return await self._request("/?type=backlinks_overview", {
            "domain": domain
        })
    
    async def backlinks(self, domain: str, limit: int = 20) -> List[Dict]:
        """Get backlinks for domain"""
        
        result = await self._request("/?type=backlinks", {
            "domain": domain,
            "display_limit": limit
        })
        
        if "data" in result:
            return result["data"]
        return []


class KeywordResearchAgent:
    """AI-powered keyword research using SEMrush + LLM"""
    
    def __init__(self, semrush: SEMrushAPI = None, llm_service = None):
        self.semrush = semrush or SEMrushAPI()
        self.llm = llm_service
    
    async def research(self, seed_keyword: str, intent: str = "all") -> Dict[str, Any]:
        """Comprehensive keyword research"""
        
        results = {
            "seed_keyword": seed_keyword,
            "analyzed_at": datetime.now().isoformat(),
            "keywords": [],
            "clusters": [],
            "opportunities": []
        }
        
        # Get related keywords
        related = await self.semrush.related_keywords(seed_keyword, 30)
        
        # Get difficulty data
        difficulty_result = await self.semrush.keyword_difficulty(seed_keyword)
        
        # Process keywords with additional data
        for kw in related[:20]:
            results["keywords"].append({
                "keyword": kw.get("Keyword", ""),
                "volume": int(kw.get("Volume", 0)),
                "cpc": float(kw.get("CPC", 0)),
                "competition": float(kw.get("Competition", 0)),
                "results": int(kw.get("Results", 0)),
                "trend": kw.get("Trend", ""),
                "intent": self._classify_intent(kw.get("Keyword", ""))
            })
        
        # Cluster keywords
        results["clusters"] = await self._cluster_keywords(results["keywords"])
        
        # Identify opportunities
        results["opportunities"] = self._identify_opportunities(results["keywords"])
        
        return results
    
    def _classify_intent(self, keyword: str) -> str:
        """Classify search intent"""
        kw_lower = keyword.lower()
        
        intent_indicators = {
            "informational": ["how", "what", "why", "guide", "tutorial", "tips", "best"],
            "navigational": ["login", "sign in", "pricing", "demo"],
            "transactional": ["buy", "order", "price", "discount", "coupon"],
            "commercial": ["review", "vs", "compare", "top", "best"]
        }
        
        for intent, indicators in intent_indicators.items():
            if any(ind in kw_lower for ind in indicators):
                return intent
        return "informational"
    
    async def _cluster_keywords(self, keywords: List[Dict]) -> List[Dict]:
        """Cluster keywords by semantic similarity"""
        
        clusters = {}
        
        for kw in keywords:
            keyword = kw.get("keyword", "").lower()
            
            # Simple clustering based on word overlap
            words = set(keyword.split())
            
            placed = False
            for cluster_id, cluster in clusters.items():
                cluster_words = set(cluster["seed"].lower().split())
                if len(words & cluster_words) > 0:
                    cluster["keywords"].append(kw)
                    placed = True
                    break
            
            if not placed:
                clusters[len(clusters)] = {
                    "seed": kw.get("keyword", ""),
                    "keywords": [kw]
                }
        
        return [
            {"cluster_id": i, "seed": c["seed"], "count": len(c["keywords"])}
            for i, c in clusters.items()
        ][:10]
    
    def _identify_opportunities(self, keywords: List[Dict]) -> List[Dict]:
        """Identify keyword opportunities"""
        
        opportunities = []
        
        for kw in keywords:
            volume = kw.get("volume", 0)
            competition = kw.get("competition", 0)
            
            # High volume, low competition = opportunity
            if volume > 500 and competition < 0.3:
                opportunities.append({
                    "keyword": kw.get("keyword"),
                    "volume": volume,
                    "competition": competition,
                    "type": "easy_win"
                })
            elif volume > 1000 and competition < 0.5:
                opportunities.append({
                    "keyword": kw.get("keyword"),
                    "volume": volume,
                    "competition": competition,
                    "type": "growth"
                })
        
        return sorted(opportunities, key=lambda x: x["volume"], reverse=True)[:10]


# Singleton
_semrush_api = None

def get_semrush_api(api_key: str = None) -> SEMrushAPI:
    global _semrush_api
    if _semrush_api is None:
        _semrush_api = SEMrushAPI(api_key)
    return _semrush_api