"""
Decision Engine - AI Agent for SEO Strategy Decisions
Acts like a senior SEO expert making strategic decisions
"""

import json
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime
from src.services.llm_service import LLMService

if TYPE_CHECKING:
    from backend.app.services.learning.decision_integrator import DecisionIntegrator
    from backend.app.services.learning.growth_scorer import GrowthScorer


@dataclass
class SEOContext:
    """Context information for decision making"""
    url: str
    keyword: str
    site_age: Optional[str] = None
    current_rankings: Optional[int] = None
    traffic: Optional[int] = None
    competitors: List[str] = None
    content_count: Optional[int] = None
    backlink_count: Optional[int] = None
    technical_issues: List[str] = None
    content_gaps: List[str] = None


class DecisionEngine:
    """
    AI Decision Making Engine
    Simulates a senior SEO expert's decision process
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        integrator: Optional["DecisionIntegrator"] = None,
        growth_scorer: Optional["GrowthScorer"] = None,
    ):
        self.llm = llm_service
        self.integrator = integrator
        self.growth_scorer = growth_scorer
        self.decision_history = []
    
    async def analyze_and_decide(
        self,
        url: str,
        keyword: str,
        context: Dict[str, Any],
        goals: List[str]
    ) -> Dict[str, Any]:
        """Main decision making process"""
        
        # Build context
        seo_context = SEOContext(
            url=url,
            keyword=keyword,
            site_age=context.get("site_age"),
            current_rankings=context.get("current_rankings"),
            traffic=context.get("traffic"),
            competitors=context.get("competitors", []),
            content_count=context.get("content_count"),
            backlink_count=context.get("backlink_count"),
            technical_issues=context.get("technical_issues", []),
            content_gaps=context.get("content_gaps", [])
        )
        
        # Phase 1: Diagnose current state
        diagnosis = await self._diagnose(seo_context)
        
        # Phase 2: Analyze competition
        competition = await self._analyze_competition(seo_context, diagnosis)
        
        # Phase 3: Identify opportunities
        opportunities = await self._identify_opportunities(
            seo_context, diagnosis, competition
        )
        
        # Phase 4: Make strategic decision
        decision = await self._make_decision(
            seo_context, diagnosis, competition, opportunities, goals
        )
        
        # Phase 5: Enrich with learned patterns (if PPO policy is available)
        if self.integrator is not None:
            enriched = await self.integrator.enrich_decision(context, decision)
            decision["enriched"] = enriched
        
        # Store in history
        history_entry = {
            "url": url,
            "keyword": keyword,
            "decision": decision,
            "timestamp": datetime.now().isoformat()
        }
        self.decision_history.append(history_entry)
        
        # Score growth trajectory (if growth scorer is available)
        if self.growth_scorer is not None:
            try:
                growth = await self.growth_scorer.score_growth(
                    url, self.decision_history
                )
                decision["growth_trajectory"] = growth
            except Exception:
                pass
        
        return decision
    
    async def _diagnose(self, context: SEOContext) -> Dict[str, Any]:
        """Diagnose current SEO state"""
        
        prompt = f"""You are a senior SEO expert. Diagnose this website's SEO health:

URL: {context.url}
Target Keyword: {context.keyword}

Current Metrics:
- Site Age: {context.site_age or 'Unknown'}
- Current Rankings: {context.current_rankings or 'Not ranking'}
- Monthly Traffic: {context.traffic or 'Unknown'}
- Content Count: {context.content_count or 'Unknown'}
- Backlinks: {context.backlink_count or 'Unknown'}
- Technical Issues: {', '.join(context.technical_issues or ['None reported'])}
- Content Gaps: {', '.join(context.content_gaps or ['None identified'])}

Provide a diagnosis as JSON:
{{
  "health_score": 0-100,
  "primary_problems": ["problem 1", "problem 2"],
  "strengths": ["strength 1", "strength 2"],
  "urgent_fixes": ["fix 1", "fix 2"],
  "diagnosis_summary": "2-3 sentence summary"
}}"""
        
        result = await self.llm.generate_json(prompt)
        return result
    
    async def _analyze_competition(
        self,
        context: SEOContext,
        diagnosis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze competitive landscape"""
        
        competitors = context.competitors or ["top 10 ranking pages"]
        comp_str = ", ".join(competitors[:5])
        
        prompt = f"""Analyze the competition for "{context.keyword}":

Competing Pages: {comp_str}

Based on the site diagnosis: {diagnosis.get('diagnosis_summary', '')}

Provide competitive analysis as JSON:
{{
  "competition_level": "high/medium/low",
  "barriers_to_beat": ["barrier 1", "barrier 2"],
  "competitive_gaps": ["gap 1", "gap 2"],
  "unique_angle": "what angle could beat competitors",
  "estimated_difficulty": 0-100
}}"""
        
        result = await self.llm.generate_json(prompt)
        return result
    
    async def _identify_opportunities(
        self,
        context: SEOContext,
        diagnosis: Dict[str, Any],
        competition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identify SEO opportunities"""
        
        prompt = f"""Identify SEO opportunities for:

URL: {context.url}
Keyword: {context.keyword}

Diagnosis: {diagnosis.get('diagnosis_summary', '')}
Competition: {competition.get('competition_level', 'medium')} level

Provide opportunities as JSON:
{{
  "quick_wins": [
    {{"opportunity": "description", "impact": "high/medium/low", "effort": "low/medium/high"}}
  ],
  "content_opportunities": ["opportunity 1", "opportunity 2"],
  "technical_opportunities": ["opportunity 1", "opportunity 2"],
  "link_building_opportunities": ["opportunity 1", "opportunity 2"],
  "total_opportunities": 0-20
}}"""
        
        result = await self.llm.generate_json(prompt)
        return result
    
    async def _make_decision(
        self,
        context: SEOContext,
        diagnosis: Dict[str, Any],
        competition: Dict[str, Any],
        opportunities: Dict[str, Any],
        goals: List[str]
    ) -> Dict[str, Any]:
        """Make final strategic decision"""
        
        goals_str = ", ".join(goals) if goals else "improve rankings"
        
        prompt = f"""As a senior SEO expert, make a strategic decision for:

Website: {context.url}
Target Keyword: {context.keyword}
Goals: {goals_str}

DIAGNOSIS:
- Health Score: {diagnosis.get('health_score', 50)}/100
- Problems: {', '.join(diagnosis.get('primary_problems', [])[:3])}
- Strengths: {', '.join(diagnosis.get('strengths', [])[:2])}

COMPETITION:
- Level: {competition.get('competition_level', 'medium')}
- Barriers: {', '.join(competition.get('barriers_to_beat', [])[:2])}
- Unique Angle: {competition.get('unique_angle', '')}

OPPORTUNITIES:
- Quick Wins: {opportunities.get('total_opportunities', 0)}
- Top Opportunity: {opportunities.get('quick_wins', [{}])[0].get('opportunity', '') if opportunities.get('quick_wins') else 'None'}

Provide your strategic decision as JSON:
{{
  "decision": "offensive/defensive/balanced/niche/authority",
  "confidence": 0.0-1.0,
  "reasoning": ["reason 1", "reason 2", "reason 3"],
  "recommended_actions": [
    {{
      "action": "description",
      "impact": "high/medium/low",
      "urgency": "immediate/this_week/this_month",
      "effort": "low/medium/high"
    }}
  ],
  "priority_order": ["action 1", "action 2", "action 3"],
  "estimated_timeline": "weeks to months",
  "resources_needed": ["resource 1", "resource 2"],
  "risk_level": "low/medium/high",
  "success_metrics": ["metric 1", "metric 2"]
}}"""
        
        result = await self.llm.generate_json(prompt)
        
        # Add metadata
        result["diagnosis"] = diagnosis
        result["competition"] = competition
        result["opportunities"] = opportunities
        result["timestamp"] = datetime.now().isoformat()
        
        return result
    
    def get_history(self) -> List[Dict]:
        """Get decision history"""
        return self.decision_history[-10:]  # Last 10 decisions


class SEOAdvisor:
    """
    SEO Advisory Agent
    Provides ongoing advice and content recommendations
    """
    
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
    
    async def generate_content(
        self,
        topic: str,
        content_type: str,
        target_keyword: str,
        style: str = "professional"
    ) -> Dict[str, Any]:
        """Generate SEO-optimized content"""
        
        content_type_guide = {
            "blog": "Comprehensive blog post with headings, examples, and actionable tips",
            "product": "Product page with features, benefits, specifications, and CTA",
            "landing": "High-converting landing page with compelling copy and CTA",
            "service": "Service page with process, benefits, testimonials, and CTA",
            "faq": "FAQ page with comprehensive Q&A format"
        }
        
        style_guide = {
            "professional": "Expert, authoritative, data-backed",
            "casual": "Friendly, approachable, easy to read",
            "technical": "Detailed, in-depth, specialist terminology",
            "persuasive": "Compelling, benefit-focused, action-oriented"
        }
        
        prompt = f"""Generate fully SEO-optimized content:

TOPIC: {topic}
TYPE: {content_type_guide.get(content_type, content_type)}
STYLE: {style_guide.get(style, style)}
TARGET KEYWORD: {target_keyword}

Requirements:
1. SEO title (50-60 chars)
2. Meta description (150-160 chars)
3. H1 and H2/H3 headings
4. 1000-2000 words of valuable content
5. Keyword naturally integrated
6. Include related LSI keywords
7. Structure for featured snippets
8. FAQ section if appropriate
9. Clear CTA

Return as JSON:
{{
  "title": "...",
  "meta_description": "...",
  "headings": ["H1", "H2", "H3..."],
  "content": "full content...",
  "schema": {{"@type": "...", ...}},
  "keywords_used": {{"primary": "...", "secondary": [...]}},
  "readability_grade": "grade level"
}}"""
        
        return await self.llm.generate_json(prompt, max_tokens=4000)
    
    async def optimize(
        self,
        content: str,
        keyword: str,
        url: str = ""
    ) -> Dict[str, Any]:
        """Optimize existing content"""
        
        prompt = f"""Optimize this content for SEO:

Current Content: {content[:3000]}

Target Keyword: {keyword}
URL: {url}

Analyze and improve:
1. Keyword placement and density
2. Content structure
3. Readability
4. Semantic completeness
5. Missing elements

Return as JSON:
{{
  "original_score": 0-100,
  "optimized_score": 0-100,
  "title_improvements": "...",
  "content_improvements": "...",
  "structural_changes": [...],
  "additional_keywords_suggested": [...],
  "improved_content": "full improved version..."
}}"""
        
        return await self.llm.generate_json(prompt, max_tokens=4000)