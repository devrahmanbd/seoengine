"""
LLM Service - Multi-Provider AI Support
Supports OpenAI, Anthropic Claude, OpenRouter, and custom endpoints
"""

import os
import json
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class LLMService:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "openai").lower()
        self.model = os.getenv("AI_MODEL", "gpt-4-turbo")
        
        # Provider-specific setup
        if self.provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif self.provider == "anthropic" or self.provider == "claude":
            import anthropic
            self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        elif self.provider == "openrouter":
            from openai import OpenAI
            self.client = OpenAI(
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1"
            )
            self.model = os.getenv("AI_MODEL", "openai/gpt-4-turbo")
        elif self.provider == "custom":
            from openai import OpenAI
            self.client = OpenAI(
                api_key=os.getenv("CUSTOM_API_KEY"),
                base_url=os.getenv("CUSTOM_API_URL", "https://api.openai.com/v1")
            )
        else:
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        json_response: bool = False
    ) -> str:
        """Generate text using configured LLM provider"""
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            if self.provider in ["anthropic", "claude"]:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages
                )
                return response.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 3000
    ) -> Dict[str, Any]:
        """Generate JSON response"""
        
        full_prompt = f"{prompt}\n\nRespond ONLY with valid JSON. No explanation."
        
        result = await self.generate(
            prompt=full_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            json_response=True
        )
        
        # Try to parse JSON
        try:
            # Handle potential markdown code blocks
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]
            
            return json.loads(result.strip())
        except:
            return {"error": "Failed to parse JSON", "raw": result}

    async def analyze_with_prompt(
        self,
        content: str,
        analysis_type: str,
        keyword: str = ""
    ) -> Dict[str, Any]:
        """Run specific type of analysis on content"""
        
        prompts = {
            "technical_audit": f"""Analyze this content for technical SEO issues:

Content: {content[:3000]}
Target Keyword: {keyword}

Return JSON:
{{
  "title_issues": [...],
  "meta_issues": [...],
  "heading_issues": [...],
  "structure_issues": [...],
  "score": 0-100,
  "critical_issues": [...]
}}""",

            "semantic_analysis": f"""Analyze this content for semantic SEO:

Content: {content[:4000]}
Target Keyword: {keyword}

Return JSON:
{{
  "topics_covered": [...],
  "entities_mentioned": [...],
  "topic_coverage": 0-100,
  "semantic_gaps": [...],
  "relevance_score": 0-100,
  "related_concepts_suggested": [...]
}}""",

            "readability": f"""Analyze readability of this content:

Content: {content[:2000]}

Return JSON:
{{
  "flesch_score": 0-100,
  "grade_level": "string",
  "sentence_lengths": [...],
  "complex_words": [...],
  "readability_issues": [...],
  "improvement_suggestions": [...]
}}""",

            "keyword_analysis": f"""Analyze keyword usage in content:

Content: {content[:3000]}
Target Keyword: {keyword}

Return JSON:
{{
  "keyword_density": 0.0-10.0,
  "keyword_placement": {{"title": bool, "headings": bool, "first_para": bool, "scattered": bool}},
  "related_keywords_found": [...],
  "LSI_keywords_missing": [...],
  "issues": [...],
  "optimization_score": 0-100
}}"""
        }

        prompt = prompts.get(analysis_type, prompts["technical_audit"])
        
        return await self.generate_json(
            prompt=prompt,
            system_prompt="You are an expert SEO analyst. Return only valid JSON."
        )

    async def get_recommendations(
        self,
        issues: List[str],
        content_type: str,
        keyword: str
    ) -> List[str]:
        """Get AI-powered recommendations based on issues"""
        
        issues_str = "\n".join([f"- {i}" for i in issues])
        
        prompt = f"""Based on these SEO issues for content about "{keyword}":

{issues_str}

Content Type: {content_type}

Provide prioritized recommendations as a JSON array:
["recommendation 1", "recommendation 2", ...]"""

        result = await self.generate_json(prompt)
        
        if isinstance(result, list):
            return result
        return []

    async def decide_strategy(
        self,
        site_info: Dict[str, Any],
        competitor_data: List[Dict],
        keyword: str,
        goals: List[str]
    ) -> Dict[str, Any]:
        """AI-powered SEO strategy decision"""
        
        site_str = json.dumps(site_info)
        comp_str = json.dumps(competitor_data[:3])
        goals_str = ", ".join(goals) if goals else "improve rankings"
        
        prompt = f"""Analyze this SEO situation and decide strategy:

SITE INFO:
{site_str}

TOP COMPETITORS:
{comp_str}

TARGET KEYWORD: {keyword}
GOALS: {goals_str}

Return JSON:
{{
  "strategy": "offensive/defensive/balanced",
  "confidence": 0.0-1.0,
  "reasoning": ["..."],
  "priority_actions": [
    {{"action": "...", "impact": "high/medium/low", "urgency": "immediate/short/long"}}
  ],
  "timeline": "estimated months to results",
  "resource_needed": "low/medium/high"
}}"""

        return await self.generate_json(prompt)


# Singleton instance
_llm_service = None

def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service