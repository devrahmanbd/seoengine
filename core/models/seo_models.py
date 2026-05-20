"""
Data Models for ZenSEO
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================
# REQUEST MODELS
# ============================================================
class AnalysisRequest(BaseModel):
    url: str
    keyword: str = ""
    compare_competitors: List[str] = []


class AuditRequest(BaseModel):
    url: Optional[str] = None
    content: Optional[str] = None
    keyword: str
    content_type: str = "article"


class DecisionRequest(BaseModel):
    url: str = ""
    keyword: str
    context: Dict[str, Any] = {}
    goals: List[str] = []


class SemanticRequest(BaseModel):
    content: str
    keyword: str
    url: str = ""
    extract_entities: bool = True


class KeywordRequest(BaseModel):
    keyword: str
    url: str = ""
    limit: int = 20


# ============================================================
# RESPONSE MODELS
# ============================================================
class AuditResult(BaseModel):
    title_analysis: Dict[str, Any]
    meta_analysis: Dict[str, Any]
    heading_analysis: Dict[str, Any]
    content_analysis: Dict[str, Any]
    readability: Dict[str, Any]
    structure: Dict[str, Any]
    eeat: Dict[str, Any]
    score: int
    issues: List[str] = []
    recommendations: List[str] = []


class SemanticResult(BaseModel):
    topics: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]
    relations: Dict[str, Any]
    relevance_score: int
    topic_coverage: int
    has_entities: bool
    knowledge_gap: List[str] = []


class KeywordResult(BaseModel):
    primary_keyword: str
    related_keywords: List[Dict[str, Any]]
    clusters: List[Dict[str, Any]]
    search_intent: str
    difficulty: int
    volume_estimate: int
    optimization_score: int
    content_gaps: List[str] = []
    issues: List[str] = []


class AnalysisResponse(BaseModel):
    url: str
    overall_score: int
    technical_audit: AuditResult
    semantic_analysis: SemanticResult
    keyword_analysis: KeywordResult
    entity_relationships: Dict[str, Any]
    recommendations: List[str]
    timestamp: str


class AuditResponse(BaseModel):
    url: str = ""
    score: int
    readability_score: int
    structure_score: int
    content_score: int
    eeat_score: int
    issues: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    timestamp: str


class SemanticResponse(BaseModel):
    topics: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]
    relationships: Dict[str, Any]
    relevance_score: int
    topic_coverage: int
    knowledge_graph: Dict[str, Any] = {}
    timestamp: str


class KeywordResponse(BaseModel):
    seed_keyword: str
    keywords: List[Dict[str, Any]]
    clusters: List[Dict[str, Any]]
    intent_distribution: Dict[str, int]
    content_opportunities: List[str] = []
    timestamp: str


class DecisionResponse(BaseModel):
    decision: str
    confidence: float
    reasoning: List[str]
    recommended_actions: List[Dict[str, Any]]
    priority_factors: Dict[str, Any] = {}
    timestamp: str


# ============================================================
# AGENT RESPONSE MODELS
# ============================================================
class SEOAdvice(BaseModel):
    summary: str
    immediate_actions: List[str]
    short_term_actions: List[str]
    long_term_actions: List[str]
    content_recommendations: List[Dict[str, Any]] = []
    technical_recommendations: List[Dict[str, Any]] = []


class ContentGenerationResult(BaseModel):
    title: str
    meta_description: str
    headings: List[str]
    content: str
    schema: Dict[str, Any]
    keyword_usage: Dict[str, int]
    readability_grade: str


class OptimizationResult(BaseModel):
    original_score: int
    optimized_score: int
    changes_made: List[str]
    improved_sections: List[Dict[str, Any]]
    new_content_suggestions: List[str] = []