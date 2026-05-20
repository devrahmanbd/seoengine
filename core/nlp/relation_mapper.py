"""
NLP - Entity Extraction and Relationship Mapping
"""

import re
from typing import Dict, List, Any, Set
from collections import defaultdict


class EntityExtractor:
    """Extracts entities from content using patterns and NLP"""
    
    def __init__(self):
        self.entity_types = {
            "PERSON": r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b',
            "ORGANIZATION": r'\b(?:Inc|LLC|Corp|Ltd|Co\.)\b',
            "PRODUCT": r'"[^"]{5,50}"',
            "LOCATION": r'\b(?:New York|London|Paris|Tokyo|San Francisco)\b',
            "DATE": r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
            "MONEY": r'\$[\d,]+(?:\.\d{2})?',
            "PERCENTAGE": r'\d+(?:\.\d+)?%',
            "EMAIL": r'\b[\w.-]+@[\w.-]+\.\w+\b',
            "URL": r'https?://[^\s]+'
        }
    
    def extract(self, content: str) -> List[Dict[str, Any]]:
        """Extract all entities from content"""
        
        entities = []
        
        # Extract by patterns
        for entity_type, pattern in self.entity_types.items():
            matches = re.findall(pattern, content)
            for match in matches:
                entities.append({
                    "type": entity_type,
                    "value": match,
                    "context": self._get_context(content, match)
                })
        
        # Extract numbers with context
        entities.extend(self._extract_numeric_entities(content))
        
        # Deduplicate
        seen = set()
        unique_entities = []
        for e in entities:
            key = f"{e['type']}:{e['value']}"
            if key not in seen:
                seen.add(key)
                unique_entities.append(e)
        
        return unique_entities
    
    def _get_context(self, content: str, entity: str, window: int = 50) -> str:
        """Get surrounding context for entity"""
        
        pos = content.find(entity)
        if pos == -1:
            return ""
        
        start = max(0, pos - window)
        end = min(len(content), pos + len(entity) + window)
        
        return content[start:end].strip()
    
    def _extract_numeric_entities(self, content: str) -> List[Dict]:
        """Extract numeric entities with patterns"""
        
        entities = []
        
        # Statistics
        stats = re.findall(r'(\d+(?:\.\d+)?)\s*(percent|%|users|visitors|years|times|people)', content, re.I)
        for num, unit in stats:
            entities.append({
                "type": "STATISTIC",
                "value": f"{num} {unit}",
                "context": ""
            })
        
        # Version numbers
        versions = re.findall(r'version\s+(\d+\.\d+(?:\.\d+)?)', content, re.I)
        for v in versions:
            entities.append({
                "type": "VERSION",
                "value": f"v{v}",
                "context": ""
            })
        
        return entities


class RelationMapper:
    """Maps relationships between entities, keywords, and content"""
    
    def __init__(self):
        self.relation_types = [
            "relates_to",
            "belongs_to",
            "part_of",
            "similar_to",
            "contradicts",
            "depends_on",
            "causes",
            "prevents"
        ]
    
    def map(
        self,
        entities: List[Dict],
        keywords: List[str],
        content: str
    ) -> Dict[str, Any]:
        """Build relationship map"""
        
        relationships = {
            "entity_to_entity": self._map_entity_to_entity(entities),
            "entity_to_keyword": self._map_entity_to_keyword(entities, keywords),
            "keyword_clusters": self._cluster_keywords(keywords, content),
            "content_structure": self._analyze_content_structure(content)
        }
        
        return relationships
    
    def _map_entity_to_entity(self, entities: List[Dict]) -> List[Dict]:
        """Find relationships between entities"""
        
        relations = []
        entity_types = defaultdict(list)
        
        # Group by type
        for e in entities:
            entity_types[e["type"]].append(e)
        
        # Create relations between same-type entities
        for etype, ents in entity_types.items():
            if len(ents) > 1:
                for i in range(len(ents) - 1):
                    relations.append({
                        "from": ents[i]["value"],
                        "to": ents[i + 1]["value"],
                        "type": "related_to",
                        "source": "same_type"
                    })
        
        return relations[:20]  # Limit
    
    def _map_entity_to_keyword(self, entities: List[Dict], keywords: List[str]) -> List[Dict]:
        """Map entities to keywords they relate to"""
        
        relations = []
        
        for entity in entities:
            for keyword in keywords[:5]:
                keyword_lower = keyword.lower()
                entity_value_lower = entity["value"].lower()
                
                if keyword_lower in entity_value_lower or entity_value_lower in keyword_lower:
                    relations.append({
                        "entity": entity["value"],
                        "keyword": keyword,
                        "type": "directly_related",
                        "strength": "strong" if keyword_lower in entity_value_lower else "weak"
                    })
        
        return relations[:15]
    
    def _cluster_keywords(self, keywords: List[str], content: str) -> List[Dict]:
        """Cluster keywords by semantic similarity"""
        
        clusters = defaultdict(list)
        content_lower = content.lower()
        
        for keyword in keywords:
            if len(keyword) < 2:
                continue
                
            # Find keyword in content
            count = content_lower.count(keyword.lower())
            
            if count == 0:
                clusters["orphaned"].append(keyword)
            elif count < 3:
                clusters["sparse"].append(keyword)
            elif count < 10:
                clusters["moderate"].append(keyword)
            else:
                clusters["frequent"].append(keyword)
        
        return [
            {"cluster": name, "keywords": kws, "count": len(kws)}
            for name, kws in clusters.items()
            if kws
        ]
    
    def _analyze_content_structure(self, content: str) -> Dict:
        """Analyze content structural relationships"""
        
        sections = content.split("\n\n")
        
        structure = {
            "total_sections": len(sections),
            "section_lengths": [],
            "has_introduction": False,
            "has_conclusion": False,
            "structure_score": 0
        }
        
        for i, section in enumerate(sections):
            words = section.split()
            structure["section_lengths"].append(len(words))
            
            # Check for intro/conclusion
            if i == 0 and len(words) > 50:
                structure["has_introduction"] = True
            
            if i == len(sections) - 1 and len(words) > 30:
                structure["has_conclusion"] = True
        
        # Calculate structure score
        if structure["has_introduction"]:
            structure["structure_score"] += 25
        if structure["has_conclusion"]:
            structure["structure_score"] += 25
        if len(sections) >= 3:
            structure["structure_score"] += 25
        if max(structure["section_lengths"], default=0) < 500:
            structure["structure_score"] += 25
        
        return structure