"""
ZenSEO Multi-Agent Brain - Production Implementation
======================================================

Real agents with actual API integrations:
- HTTP page fetching
- PageSpeed Insights API
- SEMrush API
- Google Search Console API
- LLM-powered analysis

"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib

# Import real services
from services.http_client import HTTPClient, fetch_page, FetchResult
from services.pagespeed_api import get_pagespeed_api, PageSpeedAPI
from services.semrush_api import get_semrush_api, SEMrushAPI, KeywordResearchAgent
from services.search_console_api import get_gsc_service, GSCService

# Try to import LLM service
try:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'zenseo-python', 'src'))
    from services.llm_service import get_llm_service
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


# ============================================================
# AGENT TYPES AND BASE CLASSES
# ============================================================

class AgentType(Enum):
    ORCHESTRATOR = "orchestrator"
    TECHNICAL_AUDITOR = "technical_auditor"
    CORE_WEB_VITALS = "core_web_vitals"
    KEYWORD_RESEARCHER = "keyword_researcher"
    COMPETITOR_ANALYZER = "competitor_analyzer"
    BACKLINK_AGENT = "backlink_agent"
    SCHEMA_GENERATOR = "schema_generator"
    RANK_TRACKER = "rank_tracker"
    LOCAL_SEO = "local_seo"
    CONTENT_ANALYST = "content_analyst"
    GSC_ANALYZER = "gsc_analyzer"


class AgentStatus(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    ERROR = "error"


@dataclass
class AgentTask:
    task_id: str
    task_type: str
    priority: int
    description: str
    context: Dict[str, Any]
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class BaseAgent:
    """Base class for all SEO agents with real implementations"""
    
    def __init__(self, agent_type: AgentType, name: str, description: str):
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.status = AgentStatus.IDLE
        self.current_task: Optional[AgentTask] = None
        
        # Real service instances
        self.http_client = HTTPClient()
        self.pagespeed = get_pagespeed_api()
        self.semrush = get_semrush_api()
        self.gsc = None  # Requires OAuth
        self.llm = None
        
        if LLM_AVAILABLE:
            try:
                self.llm = get_llm_service()
            except:
                pass
        
        self.capabilities: List[str] = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass
    
    async def initialize(self):
        self.status = AgentStatus.IDLE
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        self.status = AgentStatus.THINKING
        self.current_task = task
        
        try:
            self.status = AgentStatus.WORKING
            result = await self._execute_task(task)
            
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.now()
            
            self.status = AgentStatus.IDLE
            return result
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            self.status = AgentStatus.ERROR
            raise
    
    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        raise NotImplementedError


# ============================================================
# TECHNICAL AUDITOR - Real Page Analysis
# ============================================================

class TechnicalAuditorAgent(BaseAgent):
    """Senior Technical SEO Expert - Real HTTP-based analysis"""
    
    def __init__(self):
        super().__init__(
            AgentType.TECHNICAL_AUDITOR,
            "Technical Auditor",
            "Deep technical SEO analysis using real page fetching"
        )
        self.capabilities = [
            "crawlability_analysis",
            "indexation_check", 
            "redirect_audit",
            "canonical_detection",
            "hreflang_validation",
            "javascript_rendering_check",
            "core_web_vitals_fetch",
            "schema_detection",
            "mobile_usability"
        ]
    
    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute comprehensive technical audit"""
        
        context = task.context
        url = context.get("url")
        
        if not url:
            return {"error": "URL required for technical audit"}
        
        # Fetch real page data
        page_data = await fetch_page(url)
        
        if not page_data.get("success"):
            return {"error": f"Failed to fetch page: {page_data.get('error')}", 
                    "url": url}
        
        # Analyze with LLM if available
        if self.llm:
            llm_analysis = await self.llm.analyze_with_prompt(
                content=page_data.get("body_text", "")[:5000],
                analysis_type="technical_audit",
                keyword=context.get("keyword", "")
            )
        else:
            llm_analysis = {}
        
        results = {
            "url": url,
            "analyzed_at": datetime.now().isoformat(),
            "score": self._calculate_score(page_data, llm_analysis),
            
            # Real data from fetch
            "fetch": {
                "status_code": page_data.get("status_code"),
                "response_time": page_data.get("response_time"),
                "redirects": page_data.get("headers", {}).get("location"),
            },
            
            # Meta tags
            "title": {
                "tag": page_data.get("title"),
                "length": len(page_data.get("title", "")) if page_data.get("title") else 0,
                "has_keyword": context.get("keyword", "").lower() in 
                              page_data.get("title", "").lower() if page_data.get("title") else False
            },
            
            "meta_description": {
                "tag": page_data.get("meta_description"),
                "length": len(page_data.get("meta_description", "")) if page_data.get("meta_description") else 0
            },
            
            "robots": page_data.get("meta_robots"),
            
            "canonical": {
                "found": bool(page_data.get("canonical")),
                "url": page_data.get("canonical"),
                "self_referencing": page_data.get("canonical") == url
            },
            
            # Structured data
            "schema": {
                "found": len(page_data.get("json_ld_scripts", [])) > 0,
                "count": len(page_data.get("json_ld_scripts", [])),
                "types": self._extract_schema_types(page_data.get("json_ld_scripts", []))
            },
            
            # Heading structure
            "headings": {
                "h1_count": len(page_data.get("h1_tags", [])),
                "h1_tags": page_data.get("h1_tags"),
                "h2_count": len(page_data.get("h2_tags", []))
            },
            
            # Links
            "links": {
                "internal": len(page_data.get("internal_links", [])),
                "external": len(page_data.get("external_links", []))
            },
            
            # Images
            "images": {
                "total": len(page_data.get("images", [])),
                "missing_alt": len(page_data.get("images_without_alt", []))
            },
            
            # Code quality
            "code_quality": {
                "scripts": page_data.get("scripts", 0),
                "stylesheets": page_data.get("stylesheets", 0)
            },
            
            # Issues from LLM or basic analysis
            "issues": self._find_issues(page_data, llm_analysis),
            "recommendations": self._generate_recommendations(page_data, llm_analysis),
            
            # LLM-powered analysis
            "llm_analysis": llm_analysis
        }
        
        return results
    
    def _extract_schema_types(self, json_ld_scripts: List[str]) -> List[str]:
        """Extract schema.org types from JSON-LD"""
        types = []
        for script in json_ld_scripts:
            try:
                data = json.loads(script)
                if "@type" in data:
                    types.append(data["@type"])
                elif "@graph" in data and isinstance(data["@graph"], list):
                    for item in data["@graph"]:
                        if isinstance(item, dict) and "@type" in item:
                            types.append(item["@type"])
            except:
                pass
        return list(set(types))
    
    def _calculate_score(self, page_data: Dict, llm_analysis: Dict) -> int:
        """Calculate technical SEO score"""
        score = 100
        
        # Status code
        if page_data.get("status_code") != 200:
            score -= 30
        
        # Response time
        if page_data.get("response_time", 0) > 3:
            score -= 15
        
        # Missing title
        if not page_data.get("title"):
            score -= 20
        
        # Missing meta description
        if not page_data.get("meta_description"):
            score -= 10
        
        # No canonical
        if not page_data.get("canonical"):
            score -= 10
        
        # No schema
        if not page_data.get("json_ld_scripts"):
            score -= 10
        
        # Missing H1
        if not page_data.get("h1_tags"):
            score -= 15
        
        # Images without alt
        if page_data.get("images_without_alt"):
            score -= 5
        
        # LLM score if available
        if llm_analysis and "score" in llm_analysis:
            score = (score + llm_analysis["score"]) // 2
        
        return max(0, min(100, score))
    
    def _find_issues(self, page_data: Dict, llm_analysis: Dict) -> List[Dict]:
        """Identify technical issues"""
        issues = []
        
        if page_data.get("status_code") != 200:
            issues.append({
                "type": "http_status",
                "severity": "critical",
                "message": f"Page returns {page_data.get('status_code')} status"
            })
        
        if not page_data.get("title"):
            issues.append({
                "type": "missing_title",
                "severity": "critical",
                "message": "Missing title tag"
            })
        elif len(page_data.get("title", "")) > 60:
            issues.append({
                "type": "title_length",
                "severity": "medium",
                "message": "Title tag exceeds 60 characters"
            })
        
        if not page_data.get("meta_description"):
            issues.append({
                "type": "missing_meta_description",
                "severity": "high",
                "message": "Missing meta description"
            })
        
        if page_data.get("response_time", 0) > 3:
            issues.append({
                "type": "slow_response",
                "severity": "high",
                "message": f"Slow response time: {page_data.get('response_time')}s"
            })
        
        if not page_data.get("canonical"):
            issues.append({
                "type": "missing_canonical",
                "severity": "medium",
                "message": "Missing canonical URL"
            })
        
        if not page_data.get("json_ld_scripts"):
            issues.append({
                "type": "missing_schema",
                "severity": "low",
                "message": "No structured data found"
            })
        
        if page_data.get("images_without_alt"):
            issues.append({
                "type": "images_missing_alt",
                "severity": "medium",
                "message": f"{len(page_data.get('images_without_alt'))} images missing alt text"
            })
        
        # Add LLM-identified issues
        if llm_analysis and "critical_issues" in llm_analysis:
            for issue in llm_analysis["critical_issues"][:5]:
                issues.append({"type": "llm_issue", "severity": "high", "message": issue})
        
        return issues
    
    def _generate_recommendations(self, page_data: Dict, llm_analysis: Dict) -> List[str]:
        """Generate technical recommendations"""
        recs = []
        
        if not page_data.get("title"):
            recs.append("Add a descriptive title tag (50-60 characters)")
        
        if not page_data.get("meta_description"):
            recs.append("Add a compelling meta description (150-160 characters)")
        
        if not page_data.get("canonical"):
            recs.append("Add a canonical URL to prevent duplicate content issues")
        
        if not page_data.get("json_ld_scripts"):
            recs.append("Implement relevant Schema.org structured data")
        
        if page_data.get("images_without_alt"):
            recs.append("Add alt text to all images for accessibility and SEO")
        
        if len(page_data.get("h1_tags", [])) != 1:
            recs.append("Use exactly one H1 tag per page")
        
        if page_data.get("response_time", 0) > 2:
            recs.append("Optimize server response time - consider caching, CDN")
        
        if llm_analysis and "title_issues" in llm_analysis:
            for issue in llm_analysis["title_issues"][:3]:
                recs.append(f"Title: {issue}")
        
        return recs[:10]


# ============================================================
# CORE WEB VITALS AGENT - Real PageSpeed API
# ============================================================

class CoreWebVitalsAgent(BaseAgent):
    """Core Web Vitals Expert - Uses real PageSpeed API"""
    
    def __init__(self):
        super().__init__(
            AgentType.CORE_WEB_VITALS,
            "Core Web Vitals Agent",
            "Real performance metrics using Google PageSpeed API"
        )
        self.capabilities = [
            "lighthouse_audit",
            "pagespeed_analysis",
            "lcp_optimization",
            "inp_optimization",
            "cls_optimization",
            "mobile_performance",
            "desktop_performance"
        ]
    
    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute Core Web Vitals analysis using real API"""
        
        context = task.context
        url = context.get("url")
        
        if not url:
            return {"error": "URL required for Core Web Vitals analysis"}
        
        # Run real PageSpeed analysis
        ps_results = await self.pagespeed.analyze(url)
        
        if ps_results.get("error"):
            # Fallback: just fetch page and analyze structure
            return await self._basic_analysis(url)
        
        # Format results
        results = {
            "url": url,
            "analyzed_at": datetime.now().isoformat(),
            "score": ps_results.get("performance_score", 0),
            
            "desktop": {
                "score": ps_results.get("performance_score", 0),
                "core_web_vitals": ps_results.get("core_web_vitals", {}),
                "opportunities": ps_results.get("opportunities", []),
                "diagnostics": ps_results.get("diagnostics", [])
            }
        }
        
        # Also get mobile data
        mobile_results = await self.pagespeed.analyze_mobile(url)
        
        if not mobile_results.get("error"):
            results["mobile"] = {
                "score": mobile_results.get("performance_score", 0),
                "core_web_vitals": mobile_results.get("core_web_vitals", {})
            }
        
        # Calculate metrics scores
        results["metrics_summary"] = self._summarize_metrics(results)
        
        return results
    
    async def _basic_analysis(self, url: str) -> Dict:
        """Basic analysis when API not available"""
        
        page_data = await fetch_page(url)
        
        if not page_data.get("success"):
            return {"error": "Failed to fetch page"}
        
        return {
            "url": url,
            "analyzed_at": datetime.now().isoformat(),
            "score": 50,
            "warning": "Limited analysis - PageSpeed API key not configured",
            "basic_checks": {
                "render_blocking_scripts": page_data.get("scripts", 0),
                "render_blocking_styles": page_data.get("stylesheets", 0),
                "large_images": len([i for i in page_data.get("images", []) 
                                    if "src" in i])
            }
        }
    
    def _summarize_metrics(self, results: Dict) -> Dict:
        """Summarize CWV status"""
        
        desktop = results.get("desktop", {})
        cwv = desktop.get("core_web_vitals", {})
        
        summary = {
            "passing": 0,
            "needs_improvement": 0,
            "poor": 0,
            "overall_status": "unknown"
        }
        
        for metric in ["lcp", "inp", "cls"]:
            if metric in cwv:
                status = cwv[metric].get("status", "unknown")
                if status == "good":
                    summary["passing"] += 1
                elif status == "needs_improvement":
                    summary["needs_improvement"] += 1
                else:
                    summary["poor"] += 1
        
        if summary["poor"] > 0:
            summary["overall_status"] = "poor"
        elif summary["needs_improvement"] > 0:
            summary["overall_status"] = "needs_improvement"
        else:
            summary["overall_status"] = "passing"
        
        return summary


# ============================================================
# KEYWORD RESEARCHER - Real SEMrush API
# ============================================================

class KeywordResearcherAgent(BaseAgent):
    """Keyword Research Expert - Uses real SEMrush API"""
    
    def __init__(self):
        super().__init__(
            AgentType.KEYWORD_RESEARCHER,
            "Keyword Researcher",
            "Real keyword data using SEMrush API"
        )
        self.capabilities = [
            "keyword_discovery",
            "keyword_difficulty",
            "search_intent_analysis",
            "keyword_clustering",
            "competitor_keywords",
            "content_opportunities"
        ]
        self.keyword_agent = KeywordResearchAgent(self.semrush)
    
    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute keyword research"""
        
        context = task.context
        seed_keyword = context.get("keyword") or context.get("seed_keyword")
        
        if not seed_keyword:
            return {"error": "Seed keyword required for research"}
        
        # Check if API key is available
        if not self.semrush.api_key:
            return await self._llm_keyword_research(context, seed_keyword)
        
        # Use real SEMrush API
        results = await self.keyword_agent.research(seed_keyword)
        
        return results
    
    async def _llm_keyword_research(self, context: Dict, seed: str) -> Dict:
        """Fallback LLM-based keyword research"""
        
        if not self.llm:
            return {
                "error": "SEMrush API key or LLM required for keyword research",
                "keyword": seed
            }
        
        prompt = f"""Research keywords related to "{seed}" for SEO.
        
Generate a JSON response with:
{{
  "primary_keywords": ["keyword1", "keyword2"],
  "long_tail_keywords": ["long tail keyword 1", "long tail keyword 2"],
  "question_keywords": ["how to", "what is", "why"],
  "search_intent": {{"informational": [...], "commercial": [...], "transactional": [...]}},
  "difficulty_analysis": {{"easy": [...], "medium": [...], "hard": [...]}},
  "content_opportunities": ["topic1", "topic2"]
}}"""
        
        result = await self.llm.generate_json(prompt)
        result["keyword"] = seed
        result["method"] = "llm_fallback"
        
        return result


# ============================================================
# COMPETITOR ANALYZER - Real SEMrush
# ============================================================

class CompetitorAnalyzerAgent(BaseAgent):
    """Competitor Analysis - Uses SEMrush for real data"""
    
    def __init__(self):
        super().__init__(
            AgentType.COMPETITOR_ANALYZER,
            "Competitor Analyzer",
            "Real competitor analysis using SEMrush API"
        )
        self.capabilities = [
            "competitor_identification",
            "organic_competitors",
            "paid_competitors",
            "traffic_analysis",
            "keyword_gap",
            "backlink_gap"
        ]
    
    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute competitor analysis"""
        
        context = task.context
        domain = context.get("domain")
        
        if not domain:
            return {"error": "Domain required for competitor analysis"}
        
        # Check API availability
        if not self.semrush.api_key:
            return await self._llm_competitor_analysis(domain)
        
        # Real SEMrush data
        results = {
            "target_domain": domain,
            "analyzed_at": datetime.now().isoformat(),
            "organic_competitors": [],
            "paid_competitors": [],
            "keyword_overlap": []
        }
        
        # Get competitors
        competitors = await self.semrush.domain_competitors(domain)
        results["organic_competitors"] = [
            {
                "domain": c.get("Domain", ""),
                "common_keywords": int(c.get("Common Keywords", 0)),
                "visibility": float(c.get("Visibility", 0))
            }
            for c in competitors[:10]
        ]
        
        # Get paid competitors
        paid = await self.semrush.domain_advertisers(domain)
        results["paid_competitors"] = [
            {"domain": c.get("Domain", ""), "ad_keywords": c.get("Ads", 0)}
            for c in paid[:10]
        ]
        
        # Get domain's top keywords
        keywords = await self.semrush.domain_organic(domain, 20)
        results["top_keywords"] = [
            {
                "keyword": k.get("Keyword", ""),
                "volume": int(k.get("Volume", 0)),
                "position": k.get("Position", "")
            }
            for k in keywords[:20]
        ]
        
        return results
    
    async def _llm_competitor_analysis(self, domain: str) -> Dict:
        """Fallback LLM-based analysis"""
        
        if not self.llm:
            return {"error": "SEMrush API or LLM required", "domain": domain}
        
        prompt = f"""Analyze competitors for "{domain}" for SEO.

Return JSON:
{{
  "competitors": ["competitor1.com", "competitor2.com"],
  "strengths": ["..."],
  "weaknesses": ["..."],
  "keyword_gaps": ["opportunity1", "opportunity2"],
  "content_gaps": ["topic1", "topic2"],
  "backlink_opportunities": ["site1", "site2"]
}}"""
        
        return await self.llm.generate_json(prompt)


# ============================================================
# BACKLINK AGENT - Real Data
# ============================================================

class BacklinkAgent(BaseAgent):
    """Backlink Analysis - Uses SEMrush for real data"""
    
    def __init__(self):
        super().__init__(
            AgentType.BACKLINK_AGENT,
            "Backlink Analyst",
            "Real backlink profile analysis"
        )
        self.capabilities = [
            "backlink_audit",
            "link_quality",
            "toxic_links",
            "anchor_text",
            "domain_authority",
            "competitor_backlinks"
        ]
    
    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute backlink analysis"""
        
        context = task.context
        domain = context.get("domain")
        
        if not domain:
            return {"error": "Domain required for backlink analysis"}
        
        if not self.semrush.api_key:
            return {"error": "SEMrush API key required for backlink analysis", "domain": domain}
        
        # Real backlink data
        overview = await self.semrush.backlinks_overview(domain)
        backlinks = await self.semrush.backlinks(domain, 20)
        
        results = {
            "domain": domain,
            "analyzed_at": datetime.now().isoformat(),
            "overview": overview if "error" not in overview else {},
            "sample_backlinks": [
                {
                    "url": b.get(" backlinks", "").split()[0] if b.get(" backlinks") else "",
                    "domain": b.get("Domain", ""),
                    "type": b.get("Type", ""),
                    "pages": b.get("Pages", "")
                }
                for b in backlinks[:20]
            ]
        }
        
        return results


# ============================================================
# GSC ANALYZER - Google Search Console
# ============================================================

class GSCAnalyzerAgent(BaseAgent):
    """Google Search Console Expert"""
    
    def __init__(self):
        super().__init__(
            AgentType.GSC_ANALYZER,
            "GSC Analyzer",
            "Real Google Search Console data"
        )
        self.capabilities = [
            "performance_analysis",
            "ranking_opportunities",
            "index_coverage",
            "click_analysis",
            "impression_analysis"
        ]
    
    def set_gsc_credentials(self, access_token: str, site_url: str):
        """Set GSC OAuth credentials"""
        self.gsc = GSCService(access_token, site_url)
    
    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute GSC analysis"""
        
        if not self.gsc:
            return {
                "error": "GSC OAuth credentials not configured",
                "needs_oauth": True,
                "instructions": "Configure GSC_ACCESS_TOKEN and GSC_SITE_URL in .env"
            }
        
        context = task.context
        days = context.get("days", 28)
        
        # Get performance summary
        summary = await self.gsc.get_performance_summary(days)
        
        # Get ranking opportunities
        opportunities = await self.gsc.get_ranking_opportunities(days)
        
        results = {
            "analyzed_at": datetime.now().isoformat(),
            "period_days": days,
            "performance": summary,
            "opportunities": opportunities
        }
        
        return results


# ============================================================
# SCHEMA GENERATOR AGENT
# ============================================================

class SchemaGeneratorAgent(BaseAgent):
    """Schema Markup Generator - LLM-powered"""
    
    def __init__(self):
        super().__init__(
            AgentType.SCHEMA_GENERATOR,
            "Schema Generator",
            "AI-generated JSON-LD schema markup"
        )
        self.capabilities = [
            "article_schema",
            "organization_schema",
            "local_business_schema",
            "product_schema",
            "faq_schema",
            "howto_schema",
            "custom_schema"
        ]
    
    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Generate schema markup"""
        
        context = task.context
        page_type = context.get("page_type", "Article")
        page_data = context.get("page_data", {})
        
        if self.llm:
            # Use LLM to generate appropriate schema
            prompt = f"""Generate JSON-LD schema.org markup for a {page_type}.

Page data: {json.dumps(page_data)}

Return ONLY the JSON-LD schema (no explanation):
{{
  "@context": "https://schema.org",
  "@type": "...",
  ...
}}"""
            
            schema = await self.llm.generate_json(prompt)
            
            return {
                "page_type": page_type,
                "schema": schema,
                "json_ld": json.dumps(schema, indent=2)
            }
        
        # Fallback templates
        return self._template_based_schema(page_type, page_data)
    
    def _template_based_schema(self, page_type: str, data: Dict) -> Dict:
        """Template-based schema generation"""
        
        templates = {
            "Article": {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": data.get("title", ""),
                "description": data.get("description", ""),
                "author": {"@type": "Person", "name": data.get("author", "")},
                "publisher": {"@type": "Organization", "name": data.get("site_name", "")}
            },
            "Product": {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "offers": {
                    "@type": "Offer",
                    "price": data.get("price", ""),
                    "priceCurrency": data.get("currency", "USD")
                }
            }
        }
        
        schema = templates.get(page_type, templates["Article"])
        
        return {
            "page_type": page_type,
            "schema": schema,
            "json_ld": json.dumps(schema, indent=2)
        }


# ============================================================
# CONTENT ANALYST AGENT
# ============================================================

class ContentAnalystAgent(BaseAgent):
    """Content Analysis - LLM-powered"""
    
    def __init__(self):
        super().__init__(
            AgentType.CONTENT_ANALYST,
            "Content Analyst",
            "AI-powered content quality analysis"
        )
        self.capabilities = [
            "content_quality",
            "readability",
            "keyword_optimization",
            "semantic_analysis",
            "structure_analysis"
        ]
    
    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute content analysis"""
        
        context = task.context
        content = context.get("content", "")
        url = context.get("url", "")
        keyword = context.get("keyword") or context.get("target_keyword", "")
        
        if not content:
            if url:
                page_data = await fetch_page(url)
                content = page_data.get("body_text", "")
        
        if not content:
            return {"error": "Content or URL required for analysis"}
        
        results = {
            "url": url,
            "target_keyword": keyword,
            "analyzed_at": datetime.now().isoformat()
        }
        
        if self.llm:
            # Run comprehensive LLM analysis
            results["quality_analysis"] = await self.llm.analyze_with_prompt(
                content, "technical_audit", keyword
            )
            results["semantic_analysis"] = await self.llm.analyze_with_prompt(
                content, "semantic_analysis", keyword
            )
            results["readability"] = await self.llm.analyze_with_prompt(
                content, "readability"
            )
            results["keyword_analysis"] = await self.llm.analyze_with_prompt(
                content, "keyword_analysis", keyword
            )
            
            # Calculate overall score
            scores = []
            for analysis in [results["quality_analysis"], 
                           results["semantic_analysis"], 
                           results["readability"]]:
                if "score" in analysis:
                    scores.append(analysis["score"])
            
            results["overall_score"] = sum(scores) // len(scores) if scores else 50
        
        # Basic analysis if no LLM
        if not results.get("overall_score"):
            results["overall_score"] = self._basic_analysis(content, keyword)
            results["word_count"] = len(content.split())
        
        return results
    
    def _basic_analysis(self, content: str, keyword: str) -> int:
        """Basic content analysis without LLM"""
        score = 50
        
        words = content.split()
        
        if 500 <= len(words) <= 3000:
            score += 20
        elif len(words) < 300:
            score -= 20
        
        if keyword:
            keyword_lower = keyword.lower()
            content_lower = content.lower()
            
            # Keyword in title/beginning
            if keyword_lower in content_lower[:200]:
                score += 15
            
            # Keyword density
            count = content_lower.count(keyword_lower)
            density = count / len(words) * 100
            
            if 0.5 <= density <= 3:
                score += 10
        
        return max(0, min(100, score))


# ============================================================
# ORCHESTRATOR
# ============================================================

class OrchestratorAgent(BaseAgent):
    """Main orchestrator - coordinates all agents"""
    
    def __init__(self):
        super().__init__(AgentType.ORCHESTRATOR, "Orchestrator", "Coordinates SEO agents")
        self.agents: Dict[AgentType, BaseAgent] = {}
        
        self.workflows = {
            "full_audit": [
                AgentType.TECHNICAL_AUDITOR,
                AgentType.CORE_WEB_VITALS,
                AgentType.CONTENT_ANALYST
            ],
            "keyword_research": [
                AgentType.KEYWORD_RESEARCHER
            ],
            "competitor_analysis": [
                AgentType.COMPETITOR_ANALYZER,
                AgentType.BACKLINK_AGENT
            ],
            "gsc_analysis": [
                AgentType.GSC_ANALYZER
            ]
        }
    
    def register(self, agent_type: AgentType, agent: BaseAgent):
        self.agents[agent_type] = agent
    
    async def execute_workflow(self, workflow: str, context: Dict) -> Dict:
        """Execute a predefined workflow"""
        
        if workflow not in self.workflows:
            return {"error": f"Unknown workflow: {workflow}"}
        
        results = {}
        
        for agent_type in self.workflows[workflow]:
            agent = self.agents.get(agent_type)
            if not agent:
                continue
            
            task = AgentTask(
                task_id=hashlib.md5(f"{workflow}{agent_type.value}".encode()).hexdigest()[:8],
                task_type=workflow,
                priority=5,
                description=f"Workflow: {workflow}",
                context=context
            )
            
            try:
                result = await agent.process_task(task)
                results[agent_type.value] = result
            except Exception as e:
                results[agent_type.value] = {"error": str(e)}
        
        # Aggregate results
        if workflow == "full_audit":
            scores = [r.get("score", 0) for r in results.values() 
                     if isinstance(r, dict) and "score" in r]
            results["overall_score"] = sum(scores) // len(scores) if scores else 0
        
        return results


# ============================================================
# AGENT FACTORY
# ============================================================

class AgentFactory:
    """Factory for creating agents"""
    
    _agent_classes = {
        AgentType.ORCHESTRATOR: OrchestratorAgent,
        AgentType.TECHNICAL_AUDITOR: TechnicalAuditorAgent,
        AgentType.CORE_WEB_VITALS: CoreWebVitalsAgent,
        AgentType.KEYWORD_RESEARCHER: KeywordResearcherAgent,
        AgentType.COMPETITOR_ANALYZER: CompetitorAnalyzerAgent,
        AgentType.BACKLINK_AGENT: BacklinkAgent,
        AgentType.GSC_ANALYZER: GSCAnalyzerAgent,
        AgentType.SCHEMA_GENERATOR: SchemaGeneratorAgent,
        AgentType.CONTENT_ANALYST: ContentAnalystAgent,
    }
    
    @classmethod
    def create(cls, agent_type: AgentType) -> BaseAgent:
        return cls._agent_classes[agent_type]()
    
    @classmethod
    def create_all(cls) -> Dict[AgentType, BaseAgent]:
        agents = {}
        for at in AgentType:
            if at != AgentType.ORCHESTRATOR:
                try:
                    agents[at] = cls.create(at)
                except:
                    pass
        return agents


# ============================================================
# MAIN
# ============================================================

async def main():
    """Initialize and test the multi-agent system"""
    
    orchestrator = OrchestratorAgent()
    await orchestrator.initialize()
    
    agents = AgentFactory.create_all()
    
    for at, agent in agents.items():
        await agent.initialize()
        orchestrator.register(at, agent)
    
    print(f"✅ ZenSEO Multi-Agent Brain Initialized")
    print(f"   Agents: {len(agents)}")
    print(f"   Services: HTTP, PageSpeed, SEMrush, GSC, LLM")
    print(f"   Workflows: {list(orchestrator.workflows.keys())}")
    
    # Example: Technical audit
    print("\n📊 Running Technical Audit for example.com...")
    
    task = AgentTask(
        task_id="test-1",
        task_type="technical_audit",
        priority=8,
        description="Test technical audit",
        context={"url": "https://example.com", "keyword": "test"}
    )
    
    agent = agents[AgentType.TECHNICAL_AUDITOR]
    result = await agent.process_task(task)
    
    print(f"   Score: {result.get('score', 'N/A')}/100")
    print(f"   Issues: {len(result.get('issues', []))}")
    
    return orchestrator


if __name__ == "__main__":
    asyncio.run(main())