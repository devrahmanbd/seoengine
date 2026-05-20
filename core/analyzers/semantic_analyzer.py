"""
Semantic Analysis Engine
Analyzes content semantically and builds knowledge graphs
"""

import re
from typing import Dict, List, Any, Optional
from collections import defaultdict
from src.services.llm_service import LLMService


class SemanticAnalyzer:
    """Deep semantic analysis of content"""
    
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        self.concept_cache = {}
    
    async def analyze(
        self,
        content: str,
        keyword: str,
        url: str = ""
    ) -> Dict[str, Any]:
        """Main semantic analysis"""
        
        # Extract topics
        topics = self._extract_topics(content, keyword)
        
        # Extract concepts
        concepts = self._extract_concepts(content)
        
        # Calculate semantic metrics
        metrics = self._calculate_semantic_metrics(content, keyword, topics, concepts)
        
        # Identify gaps
        gaps = self._identify_gaps(keyword, topics, concepts)
        
        return {
            "topics": topics,
            "concepts": concepts,
            "topic_coverage": metrics["topic_coverage"],
            "relevance_score": metrics["relevance_score"],
            "semantic_gaps": gaps,
            "has_entities": len(concepts) > 0,
            "knowledge_graph": self._build_knowledge_graph(topics, concepts)
        }
    
    async def deep_analyze(
        self,
        content: str,
        keyword: str,
        url: str = "",
        extract_entities: bool = True
    ) -> Dict[str, Any]:
        """Deep semantic analysis with LLM enhancement"""
        
        # Basic analysis
        basic = await self.analyze(content, keyword, url)
        
        # LLM-enhanced analysis
        llm_analysis = await self.llm.analyze_with_prompt(
            content=content[:4000],
            analysis_type="semantic_analysis",
            keyword=keyword
        )
        
        return {
            "topics": basic["topics"],
            "entities": llm_analysis.get("entities_mentioned", []),
            "relations": self._extract_relations(content),
            "relevance_score": llm_analysis.get("relevance_score", basic["relevance_score"]),
            "topic_coverage": llm_analysis.get("topic_coverage", basic["topic_coverage"]),
            "knowledge_graph": basic["knowledge_graph"],
            "topic_suggestions": llm_analysis.get("related_concepts_suggested", []),
            "semantic_gaps": basic["semantic_gaps"]
        }
    
    def _extract_topics(self, content: str, keyword: str) -> List[Dict[str, Any]]:
        """Extract main topics from content"""
        topics = []
        
        # Split content into sections
        paragraphs = content.split("\n\n")
        
        # Find topic indicators
        topic_keywords = [
            "introduction", "overview", "summary", "benefits", "advantages",
            "features", "how to", "steps", "tips", "examples", "types",
            "vs", "compared", "FAQ", "questions"
        ]
        
        for i, para in enumerate(paragraphs):
            para_lower = para.lower()
            
            # Check for topic keywords
            for tk in topic_keywords:
                if tk in para_lower:
                    topics.append({
                        "id": i,
                        "keyword": tk,
                        "content_preview": para[:100] + "...",
                        "word_count": len(para.split())
                    })
                    break
        
        # Add keyword as main topic
        if keyword:
            topics.insert(0, {
                "id": "main",
                "keyword": keyword,
                "content_preview": "Main topic",
                "is_primary": True
            })
        
        return topics[:20]  # Limit to top 20
    
    def _extract_concepts(self, content: str) -> List[str]:
        """Extract key concepts from content"""
        concepts = set()
        
        # Find capitalized phrases (likely proper nouns/concepts)
        caps_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        caps_matches = re.findall(caps_pattern, content)
        
        # Filter common words
        exclude = {"The", "This", "That", "These", "Those", "Google", "WordPress", "Facebook", "Twitter"}
        concepts.update([m for m in caps_matches if m not in exclude])
        
        # Find phrases in quotes
        quoted = re.findall(r'"([^"]+)"', content)
        concepts.update(quoted)
        
        # Technical terms (words with common suffixes)
        technical_suffixes = ["tion", "ing", "ment", "ness", "ity", "ology", "ology"]
        words = content.split()
        for word in words:
            if any(word.endswith(s) for s in technical_suffixes) and len(word) > 8:
                concepts.add(word)
        
        return list(concepts)[:30]
    
    def _calculate_semantic_metrics(
        self,
        content: str,
        keyword: str,
        topics: List[Dict],
        concepts: List[str]
    ) -> Dict[str, int]:
        """Calculate semantic quality metrics"""
        
        word_count = len(content.split())
        
        # Topic coverage
        topic_coverage = min(100, int((len(topics) / 10) * 100))
        
        # Relevance score
        relevance = 50
        
        # Keyword in first paragraph
        first_para = content.split("\n\n")[0].lower() if "\n\n" in content else content.lower()
        if keyword.lower() in first_para:
            relevance += 15
        
        # Topic mentions
        keyword_lower = keyword.lower()
        topic_mentions = sum(1 for t in topics if keyword_lower in t.get("keyword", "").lower())
        relevance += min(20, topic_mentions * 5)
        
        # Concept diversity
        if word_count > 100:
            concept_density = len(concepts) / (word_count / 100)
            if concept_density > 3:
                relevance += 15
        
        return {
            "topic_coverage": topic_coverage,
            "relevance_score": min(100, relevance)
        }
    
    def _identify_gaps(
        self,
        keyword: str,
        topics: List[Dict],
        concepts: List[str]
    ) -> List[str]:
        """Identify semantic gaps in content"""
        
        # Suggested related topics based on keyword
        keyword_lower = keyword.lower()
        
        gap_topics = {
            "seo": ["technical seo", "link building", "local seo", "mobile seo", "core web vitals"],
            "marketing": ["content marketing", "social media", "email marketing", "ppc", "analytics"],
            "business": ["strategy", "growth", "sales", "customer acquisition", "retention"],
            "technology": ["implementation", "integration", "security", "optimization", "automation"],
            "health": ["symptoms", "treatment", "prevention", "causes", "diagnosis"]
        }
        
        gaps = []
        
        # Find related topics not covered
        for category, related in gap_topics.items():
            if category in keyword_lower:
                for r in related:
                    if not any(r in t.get("keyword", "").lower() for t in topics):
                        gaps.append(f"Add content about: {r}")
        
        return gaps[:5]
    
    def _build_knowledge_graph(
        self,
        topics: List[Dict],
        concepts: List[str]
    ) -> Dict[str, Any]:
        """Build a simple knowledge graph"""
        
        graph = {
            "nodes": [],
            "edges": []
        }
        
        # Add topic nodes
        for topic in topics[:10]:
            graph["nodes"].append({
                "id": topic.get("id", ""),
                "label": topic.get("keyword", ""),
                "type": "topic"
            })
        
        # Add concept nodes
        for concept in concepts[:10]:
            graph["nodes"].append({
                "id": concept,
                "label": concept,
                "type": "concept"
            })
        
        # Add edges (simple connection between sequential topics)
        for i in range(len(graph["nodes"]) - 1):
            graph["edges"].append({
                "from": graph["nodes"][i]["id"],
                "to": graph["nodes"][i+1]["id"],
                "type": "related_to"
            })
        
        return graph
    
    def _extract_relations(self, content: str) -> Dict[str, List[str]]:
        """Extract semantic relations between entities"""
        
        relations = defaultdict(list)
        
        # Common relation patterns
        patterns = [
            (r'(\w+) is a (\w+)', 'is_a'),
            (r'(\w+) can (\w+)', 'can_do'),
            (r'(\w+) vs (\w+)', 'versus'),
            (r'(\w+) and (\w+)', 'related_to'),
            (r'(\w+) with (\w+)', 'associated_with')
        ]
        
        for pattern, rel_type in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:
                    relations[rel_type].append({
                        "from": match[0],
                        "to": match[1]
                    })
        
        return dict(relations)


class KeywordAnalyzer:
    """Comprehensive keyword analysis"""
    
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
    
    async def analyze(
        self,
        content: str,
        target_keyword: str
    ) -> Dict[str, Any]:
        """Analyze keyword usage in content"""
        
        # Extract keywords from content
        content_keywords = self._extract_keywords(content)
        
        # Calculate metrics
        density = self._calculate_density(content, target_keyword)
        placement = self._analyze_placement(content, target_keyword)
        
        # Find related keywords
        related = self._find_related_keywords(content, target_keyword)
        
        # Identify LSI keywords
        lsi = self._find_lsi_keywords(content, target_keyword)
        
        return {
            "primary_keyword": target_keyword,
            "density": density,
            "placement": placement,
            "related_keywords": related,
            "lsi_keywords": lsi,
            "issues": self._identify_issues(density, placement, related),
            "optimization_score": self._calculate_optimization_score(density, placement, related)
        }
    
    async def research(
        self,
        seed_keyword: str,
        url: str = "",
        limit: int = 20
    ) -> Dict[str, Any]:
        """Comprehensive keyword research"""
        
        # Get LLM-powered keyword suggestions
        suggestions = await self._get_ai_suggestions(seed_keyword, limit)
        
        # Cluster keywords
        clusters = self._cluster_keywords(suggestions)
        
        # Determine intent
        intents = self._analyze_intents(suggestions)
        
        # Find content opportunities
        opportunities = self._find_content_opportunities(seed_keyword, suggestions)
        
        return {
            "seed_keyword": seed_keyword,
            "keywords": suggestions,
            "clusters": clusters,
            "intent_distribution": intents,
            "content_opportunities": opportunities
        }
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract significant keywords from content"""
        
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        word_freq = defaultdict(int)
        
        for word in words:
            if word not in stop_words:
                word_freq[word] += 1
        
        # Return sorted by frequency
        return sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:50]
    
    def _calculate_density(self, content: str, keyword: str) -> float:
        """Calculate keyword density"""
        
        words = content.lower().split()
        keyword_count = content.lower().count(keyword.lower())
        
        if not words:
            return 0.0
        
        return round((keyword_count / len(words)) * 100, 2)
    
    def _analyze_placement(self, content: str, keyword: str) -> Dict[str, bool]:
        """Analyze keyword placement"""
        
        keyword_lower = keyword.lower()
        content_lower = content.lower()
        
        first_para = content.split("\n\n")[0].lower() if "\n\n" in content else ""
        
        return {
            "in_title": keyword_lower in content_lower[:200],
            "in_first_paragraph": keyword_lower in first_para[:500],
            "in_headings": any(keyword_lower in h.lower() for h in content.split("\n")),
            "in_conclusion": keyword_lower in content_lower[-500:],
            "distributed": True  # Simple check
        }
    
    def _find_related_keywords(self, content: str, target: str) -> List[str]:
        """Find semantically related keywords"""
        
        # Use common co-occurrence patterns
        related = []
        
        # Common related terms
        related_terms = {
            "seo": ["optimization", "rankings", "traffic", "backlinks", "keywords"],
            "marketing": ["strategy", "campaign", "audience", "conversion", "brand"],
            "business": ["revenue", "growth", "profit", "customers", "market"]
        }
        
        target_lower = target.lower()
        for category, terms in related_terms.items():
            if category in target_lower:
                for term in terms:
                    if term in content.lower():
                        related.append(term)
        
        return related[:10]
    
    def _find_lsi_keywords(self, content: str, target: str) -> List[str]:
        """Find LSI keywords"""
        
        # Simple LSI - common semantically related words
        lsi_map = {
            "guide": ["tutorial", "how to", "steps", "complete", "comprehensive"],
            "best": ["top", "review", "comparison", "ranking", "recommend"],
            "tips": ["advice", "tricks", "hacks", "secrets", "strategies"]
        }
        
        lsi = []
        content_lower = content.lower()
        
        for main, variants in lsi_map.items():
            if main in content_lower:
                lsi.extend([v for v in variants if v in content_lower])
        
        return list(set(lsi))[:10]
    
    def _identify_issues(self, density: float, placement: Dict, related: List) -> List[str]:
        """Identify keyword issues"""
        
        issues = []
        
        if density < 0.5:
            issues.append("Low keyword density")
        elif density > 3:
            issues.append("Keyword stuffing detected")
        
        if not placement.get("in_first_paragraph"):
            issues.append("Keyword not in introduction")
        
        if not placement.get("in_headings"):
            issues.append("Keyword not in subheadings")
        
        if len(related) < 3:
            issues.append("Few related keywords used")
        
        return issues
    
    def _calculate_optimization_score(
        self,
        density: float,
        placement: Dict,
        related: List
    ) -> int:
        """Calculate keyword optimization score"""
        
        score = 50
        
        # Density score
        if 1 <= density <= 2.5:
            score += 25
        elif density > 0.5:
            score += 10
        
        # Placement score
        placement_score = sum(placement.values())
        score += min(15, placement_score * 5)
        
        # Related keywords
        score += min(10, len(related) * 2)
        
        return min(100, max(0, score))
    
    async def _get_ai_suggestions(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """Get AI-powered keyword suggestions"""
        
        prompt = f"""Generate {limit} related keywords for "{keyword}". 
Include various search intents.

Return as JSON array:
[{{"keyword": "...", "intent": "informational/commercial/navigational/transactional", "difficulty": 0-100}}]"""

        result = await self.llm.generate_json(prompt)
        
        if isinstance(result, list):
            return result[:limit]
        return []
    
    def _cluster_keywords(self, keywords: List[Dict]) -> List[Dict]:
        """Cluster keywords by similarity"""
        
        clusters = []
        
        # Simple clustering by intent
        by_intent = defaultdict(list)
        for kw in keywords:
            intent = kw.get("intent", "informational")
            by_intent[intent].append(kw)
        
        for intent, kws in by_intent.items():
            clusters.append({
                "name": intent,
                "keywords": [k["keyword"] for k in kws],
                "count": len(kws)
            })
        
        return clusters
    
    def _analyze_intents(self, keywords: List[Dict]) -> Dict[str, int]:
        """Analyze intent distribution"""
        
        intents = defaultdict(int)
        for kw in keywords:
            intent = kw.get("intent", "informational")
            intents[intent] += 1
        
        return dict(intents)
    
    def _find_content_opportunities(
        self,
        seed: str,
        keywords: List[Dict]
    ) -> List[str]:
        """Find content opportunities"""
        
        opportunities = []
        
        # Find low-difficulty keywords
        low_diff = [k for k in keywords if k.get("difficulty", 100) < 40]
        
        for kw in low_diff[:3]:
            opportunities.append(f"Target keyword: {kw['keyword']} (low competition)")
        
        # High-volume commercial intents
        commercial = [k for k in keywords if k.get("intent") == "commercial"]
        if commercial:
            opportunities.append(f"Create buying guide for: {commercial[0]['keyword']}")
        
        return opportunities[:5]