"""
PageSpeed Insights API Integration
Uses Google PageSpeed Insights API for real Core Web Vitals data
"""

import os
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime


class PageSpeedAPI:
    """Google PageSpeed Insights API integration"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("PAGESPEED_API_KEY", "")
        self.base_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    async def analyze(self, url: str, category: str = "performance") -> Dict[str, Any]:
        """Run PageSpeed analysis on a URL"""
        
        params = {
            "url": url,
            "key": self.api_key,
            "category": category,
            "strategy": "desktop"
        }
        
        if self.api_key:
            params["category"] = "performance,accessibility,best-practices,seo"
        
        try:
            async with aiohttp.ClientTimeout(total=60) as timeout:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(self.base_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self._parse_results(data)
                        elif response.status == 403:
                            return {"error": "API key required", "needs_api_key": True}
                        else:
                            return {"error": f"HTTP {response.status}"}
        except asyncio.TimeoutError:
            return {"error": "Request timeout"}
        except Exception as e:
            return {"error": str(e)}
    
    async def analyze_mobile(self, url: str) -> Dict[str, Any]:
        """Run mobile PageSpeed analysis"""
        
        params = {
            "url": url,
            "key": self.api_key,
            "strategy": "mobile"
        }
        
        if self.api_key:
            params["category"] = "performance"
        
        try:
            async with aiohttp.ClientTimeout(total=60) as timeout:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(self.base_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self._parse_mobile_results(data)
                        else:
                            return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_results(self, data: Dict) -> Dict[str, Any]:
        """Parse PageSpeed API response"""
        
        try:
            lighthouse = data.get("lighthouseResult", {})
            categories = lighthouse.get("categories", {})
            
            # Core Web Vitals
            audits = lighthouse.get("audits", {})
            
            lcp = audits.get("largest-contentful-paint", {})
            inp = audits.get("interactive", {})
            cls = audits.get("cumulative-layout-shift", {})
            fcp = audits.get("first-contentful-paint", {})
            tbt = audits.get("total-blocking-time", {})
            si = audits.get("speed-index", {})
            
            # Thresholds
            lcp_value = lcp.get("numericValue", 0) / 1000  # Convert to seconds
            inp_value = inp.get("numericValue", 0)
            cls_value = cls.get("numericValue", 0)
            
            return {
                "success": True,
                "url": data.get("id"),
                "analyzed_at": datetime.now().isoformat(),
                
                # Scores (0-100)
                "performance_score": int(categories.get("performance", {}).get("score", 0) * 100),
                "accessibility_score": int(categories.get("accessibility", {}).get("score", 0) * 100),
                "best_practices_score": int(categories.get("best-practices", {}).get("score", 0) * 100),
                "seo_score": int(categories.get("seo", {}).get("score", 0) * 100),
                
                # Core Web Vitals
                "core_web_vitals": {
                    "lcp": {
                        "value": round(lcp_value, 2),
                        "unit": "seconds",
                        "status": self._get_lcp_status(lcp_value),
                        "display_value": lcp.get("displayValue", "")
                    },
                    "inp": {
                        "value": round(inp_value, 2),
                        "unit": "milliseconds", 
                        "status": self._get_inp_status(inp_value),
                        "display_value": inp.get("displayValue", "")
                    },
                    "cls": {
                        "value": round(cls_value, 3),
                        "unit": "score",
                        "status": self._get_cls_status(cls_value),
                        "display_value": cls.get("displayValue", "")
                    },
                    "fcp": {
                        "value": round(fcp.get("numericValue", 0) / 1000, 2),
                        "unit": "seconds",
                        "display_value": fcp.get("displayValue", "")
                    },
                    "tbt": {
                        "value": round(tbt.get("numericValue", 0), 2),
                        "unit": "milliseconds",
                        "display_value": tbt.get("displayValue", "")
                    },
                    "si": {
                        "value": round(si.get("numericValue", 0) / 1000, 2),
                        "unit": "seconds",
                        "display_value": si.get("displayValue", "")
                    }
                },
                
                # Opportunities
                "opportunities": self._extract_opportunities(audits),
                
                # Diagnostics
                "diagnostics": self._extract_diagnostics(audits)
            }
        except Exception as e:
            return {"error": f"Failed to parse results: {str(e)}", "raw": data}
    
    def _parse_mobile_results(self, data: Dict) -> Dict[str, Any]:
        """Parse mobile-specific results"""
        
        parsed = self._parse_results(data)
        if "success" in parsed:
            parsed["device"] = "mobile"
        return parsed
    
    def _get_lcp_status(self, value: float) -> str:
        if value <= 2.5:
            return "good"
        elif value <= 4.0:
            return "needs_improvement"
        return "poor"
    
    def _get_inp_status(self, value: float) -> str:
        if value <= 200:
            return "good"
        elif value <= 500:
            return "needs_improvement"
        return "poor"
    
    def _get_cls_status(self, value: float) -> str:
        if value <= 0.1:
            return "good"
        elif value <= 0.25:
            return "needs_improvement"
        return "poor"
    
    def _extract_opportunities(self, audits: Dict) -> list:
        """Extract optimization opportunities"""
        opportunities = []
        
        priority_audits = [
            "render-blocking-resources",
            "unused-css-rules",
            "unused-javascript",
            "large-javascript-payloads",
            "main-thread-work",
            "dom-size",
            "server-response-time",
            "redirects",
            "preload-lcp-image"
        ]
        
        for audit_id in priority_audits:
            if audit_id in audits:
                audit = audits[audit_id]
                if audit.get("score", 1) < 0.9:
                    opportunities.append({
                        "id": audit_id,
                        "title": audit.get("title", ""),
                        "description": audit.get("description", ""),
                        "score": audit.get("score", 0),
                        "display_value": audit.get("displayValue", "")
                    })
        
        return opportunities[:10]
    
    def _extract_diagnostics(self, audits: Dict) -> list:
        """Extract diagnostic information"""
        diagnostics = []
        
        diagnostic_audits = [
            "doctype",
            "charset",
            "meta-viewport",
            "html-has-lang",
            "image-alt",
            "link-text",
            "meta-description",
            "document-title",
            "link-rel",
            "http-status-code"
        ]
        
        for audit_id in diagnostic_audits:
            if audit_id in audits:
                audit = audits[audit_id]
                if audit.get("score", 1) < 1:
                    diagnostics.append({
                        "id": audit_id,
                        "title": audit.get("title", ""),
                        "description": audit.get("description", "")[:200]
                    })
        
        return diagnostics[:10]


# Singleton
_pagespeed_api = None

def get_pagespeed_api(api_key: str = None) -> PageSpeedAPI:
    global _pagespeed_api
    if _pagespeed_api is None:
        _pagespeed_api = PageSpeedAPI(api_key)
    return _pagespeed_api