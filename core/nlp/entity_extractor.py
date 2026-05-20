"""
Entity Extractor
"""

from typing import Dict, List, Any, Set
import re
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