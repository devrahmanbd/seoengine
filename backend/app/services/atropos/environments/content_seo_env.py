import re
import time
from html.parser import HTMLParser

import httpx

from app.services.atropos.base_env import SEOEnvironment, SEOAction, State


class _ContentHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.headings = []
        self.faq_found = False
        self.schemas = []
        self._in_schema = False
        self._schema_depth = 0
        self._in_faq = False
        self._faq_depth = 0
        self._skip_tags = {"script", "style", "noscript"}

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        attrs_map = dict(attrs)
        if t == "script":
            script_type = attrs_map.get("type", "")
            if "ld+json" in script_type:
                self._in_schema = True
                self._schema_depth = 0
            self._skip_tags.add(t)
        if self._in_schema:
            self._schema_depth += 1
        if t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(t)

    def handle_endtag(self, tag):
        t = tag.lower()
        if self._in_schema:
            self._schema_depth -= 1
            if self._schema_depth <= 0:
                self._in_schema = False
                self.schemas.append(True)

    def handle_data(self, data):
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self.text_parts)


_CONTINUING_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "it", "its", "this", "that", "these", "those", "i", "you", "he",
    "she", "we", "they", "me", "him", "her", "us", "them", "my", "your",
    "his", "her", "our", "their", "no", "not", "nor", "so", "than", "too",
    "very", "just", "about", "up", "down", "out", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "what", "which", "who",
    "whom", "if", "because", "while", "after", "before", "until",
}


def _compute_readability(text: str) -> float:
    sentences = re.split(r"[.!?]+", text)
    sentence_count = max(len([s for s in sentences if s.strip()]), 1)
    words = re.findall(r"[a-zA-Z]+", text)
    word_count = len(words)
    if word_count == 0:
        return 0.0
    syllable_count = 0
    for w in words:
        if len(w) <= 3:
            syllable_count += 1
        else:
            syllable_count += max(1, len(re.findall(r"[aeiouyAEIOUY]+", w)))
    avg_syllables = syllable_count / word_count
    avg_words_per_sentence = word_count / sentence_count
    score = 206.835 - 1.015 * avg_words_per_sentence - 84.6 * avg_syllables
    return max(0.0, min(100.0, score))


def _extract_entities(text: str) -> list[str]:
    words = re.findall(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*", text)
    entities = [w for w in words if len(w) > 2 and w.lower() not in _CONTINUING_WORDS]
    return entities


def _heading_structure_score(headings: list[str]) -> float:
    if not headings:
        return 0.0
    levels = []
    for h in headings:
        level = int(h[1]) if len(h) == 2 and h[1].isdigit() else 0
        levels.append(level)
    if levels[0] != 1:
        return 0.3
    score = 1.0
    for i in range(1, len(levels)):
        diff = levels[i] - levels[i - 1]
        if diff > 1:
            score -= 0.2
        elif diff < 0:
            score -= 0.1
    return max(score, 0.0)


class ContentSEOEnv(SEOEnvironment):
    WEIGHTS = {
        "word_count_score": 0.15,
        "readability_score": 0.20,
        "keyword_density_score": 0.15,
        "entity_count_score": 0.10,
        "heading_structure_score": 0.20,
        "has_faq": 0.10,
        "has_schema": 0.10,
    }

    def __init__(self, site_id: str, max_steps: int = 10):
        self.site_id = site_id
        self.max_steps = max_steps
        self.current_step = 0
        self.metrics = self._default_metrics()
        self._html = ""
        self._text = ""
        self._headings = []
        self._keywords: list[str] = []

    def _default_metrics(self) -> dict:
        return {
            "word_count": 0,
            "readability_score": 0.0,
            "keyword_density": 0.0,
            "target_keyword": "",
            "entity_count": 0,
            "heading_structure_score": 0.0,
            "has_faq": False,
            "has_schema": False,
            "content_score": 0.0,
        }

    async def reset(self) -> State:
        self.current_step = 0
        await self._fetch_and_parse()
        self.metrics["content_score"] = self._compute_content_score(self.metrics)
        return State(
            site_id=self.site_id,
            metrics=dict(self.metrics),
            timestamp=time.time(),
            features=[self.metrics["content_score"]],
        )

    async def _fetch_and_parse(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(self.site_id)
                self._html = resp.text
        except Exception:
            self._html = ""
            return
        if not self._html:
            return
        parser = _ContentHTMLParser()
        try:
            parser.feed(self._html)
        except Exception:
            pass
        self._text = parser.get_text()
        self._headings = parser.headings
        self.metrics["word_count"] = len(re.findall(r"[a-zA-Z]+", self._text))
        self.metrics["readability_score"] = _compute_readability(self._text)
        self.metrics["heading_structure_score"] = _heading_structure_score(
            self._headings
        )
        entities = _extract_entities(self._text)
        self.metrics["entity_count"] = len(entities)
        self.metrics["has_faq"] = bool(
            re.search(
                r"faq|frequently asked questions|questions\s+and\s+answers",
                self._text,
                re.IGNORECASE,
            )
        )
        self.metrics["has_schema"] = len(parser.schemas) > 0

    def _compute_content_score(self, metrics: dict) -> float:
        scores = {}
        wc = metrics.get("word_count", 0)
        if wc >= 1500:
            scores["word_count_score"] = 1.0
        elif wc >= 1000:
            scores["word_count_score"] = 0.8
        elif wc >= 500:
            scores["word_count_score"] = 0.5
        elif wc >= 200:
            scores["word_count_score"] = 0.3
        else:
            scores["word_count_score"] = 0.1

        rd = metrics.get("readability_score", 0.0)
        if rd >= 70:
            scores["readability_score"] = 1.0
        elif rd >= 60:
            scores["readability_score"] = 0.8
        elif rd >= 50:
            scores["readability_score"] = 0.6
        elif rd >= 30:
            scores["readability_score"] = 0.3
        else:
            scores["readability_score"] = 0.1

        kd = metrics.get("keyword_density", 0.0)
        if 0.5 <= kd <= 2.5:
            scores["keyword_density_score"] = 1.0
        elif 2.5 < kd <= 4.0:
            scores["keyword_density_score"] = 0.7
        elif 0.1 <= kd < 0.5:
            scores["keyword_density_score"] = 0.5
        else:
            scores["keyword_density_score"] = 0.1

        ec = metrics.get("entity_count", 0)
        if ec >= 15:
            scores["entity_count_score"] = 1.0
        elif ec >= 10:
            scores["entity_count_score"] = 0.8
        elif ec >= 5:
            scores["entity_count_score"] = 0.5
        elif ec >= 1:
            scores["entity_count_score"] = 0.2
        else:
            scores["entity_count_score"] = 0.0

        scores["heading_structure_score"] = metrics.get("heading_structure_score", 0.0)
        scores["has_faq"] = 1.0 if metrics.get("has_faq") else 0.0
        scores["has_schema"] = 1.0 if metrics.get("has_schema") else 0.0

        total = sum(
            scores.get(key, 0.0) * weight
            for key, weight in self.WEIGHTS.items()
        )
        return min(max(total, 0.0), 1.0)

    async def step(self, action: SEOAction) -> tuple[State, float, bool, dict]:
        self.current_step += 1
        old_score = self.metrics.get("content_score", 0.0)
        action_result = {"applied": False, "message": "Unknown action"}
        readability_delta = 0.0
        keyword_density_delta = 0.0
        entity_coverage_delta = 0.0

        if action.action_type == "optimize_content":
            target_words = action.params.get("target_word_count", 1500)
            current_wc = self.metrics["word_count"]
            old_kd = self.metrics.get("keyword_density", 0.0)
            if current_wc < target_words:
                increase = min(target_words - current_wc, 500)
                self.metrics["word_count"] = current_wc + increase
                if self.metrics["readability_score"] < 60:
                    self.metrics["readability_score"] = min(
                        self.metrics["readability_score"] + 5.0, 70.0
                    )
                kw = self.metrics.get("target_keyword", "")
                if kw:
                    old_kd = self.metrics.get("keyword_density", 0.0)
                    simulated_increase = max(increase / current_wc, 0.1) if current_wc > 0 else 0.1
                    self.metrics["keyword_density"] = (old_kd * current_wc + 1.5 * simulated_increase * current_wc) / (current_wc + increase)
                added_entities = max(increase // 50, 5)
                self.metrics["entity_count"] += added_entities
                readability_delta = 5.0
                keyword_density_delta = self.metrics["keyword_density"] - old_kd
                entity_coverage_delta = added_entities / 20.0
                action_result = {
                    "applied": True,
                    "message": f"Content expanded by {increase} words",
                }
            else:
                action_result = {"applied": True, "message": "Content already meets target"}

        elif action.action_type == "add_entities":
            entities_to_add = action.params.get("entities", [])
            count = len(entities_to_add)
            if count > 0:
                self.metrics["entity_count"] += count
                entity_coverage_delta = count / 20.0
                if self.metrics["word_count"] > 0:
                    self.metrics["keyword_density"] = self._recalc_density(
                        self.metrics.get("target_keyword", "")
                    )
                action_result = {
                    "applied": True,
                    "message": f"Added {count} named entities",
                }
            else:
                entity_coverage_delta = 3 / 20.0
                self.metrics["entity_count"] += 3
                action_result = {"applied": True, "message": "Added 3 inferred entities"}

        elif action.action_type == "improve_readability":
            target_level = action.params.get("target_readability", 70.0)
            current_rd = self.metrics["readability_score"]
            if current_rd < target_level:
                improvement = min(target_level - current_rd, 15.0)
                self.metrics["readability_score"] = current_rd + improvement
                readability_delta = improvement
                action_result = {
                    "applied": True,
                    "message": f"Readability improved by {improvement:.1f} points",
                }
            else:
                action_result = {
                    "applied": True,
                    "message": "Readability already meets target",
                }

        elif action.action_type == "add_faq_schema":
            if not self.metrics["has_faq"]:
                self.metrics["has_faq"] = True
                faq_count = action.params.get("faq_count", 3)
                self.metrics["word_count"] += faq_count * 30
                entity_coverage_delta = 0.05
                action_result = {
                    "applied": True,
                    "message": f"FAQ schema with {faq_count} items added",
                }
            else:
                action_result = {"applied": True, "message": "FAQ schema already present"}

        elif action.action_type == "restructure_headings":
            self._headings = ["h1", "h2", "h2", "h3", "h2", "h3"]
            new_score = _heading_structure_score(self._headings)
            old_h_score = self.metrics["heading_structure_score"]
            self.metrics["heading_structure_score"] = new_score
            readability_delta = 0.0
            keyword_density_delta = 0.0
            entity_coverage_delta = new_score - old_h_score
            action_result = {
                "applied": True,
                "message": "Heading hierarchy restructured",
            }

        new_score = self._compute_content_score(self.metrics)
        self.metrics["content_score"] = new_score

        reward = max(
            min(
                (readability_delta / 100.0) * 0.35
                + keyword_density_delta * 0.30
                + entity_coverage_delta * 0.35,
                1.0,
            ),
            -0.5,
        )

        done = new_score > 0.8 or self.current_step >= self.max_steps

        info = {
            "action_result": action_result,
            "new_metrics": dict(self.metrics),
            "reward_components": {
                "readability_delta": readability_delta / 100.0,
                "keyword_density_delta": keyword_density_delta,
                "entity_coverage_delta": entity_coverage_delta,
            },
        }

        return (
            State(
                site_id=self.site_id,
                metrics=dict(self.metrics),
                timestamp=time.time(),
                features=[new_score],
            ),
            reward,
            done,
            info,
        )

    def _recalc_density(self, keyword: str) -> float:
        if not keyword or self.metrics["word_count"] == 0:
            return self.metrics.get("keyword_density", 0.0)
        text_lower = self._text.lower()
        kw_lower = keyword.lower()
        count = text_lower.count(kw_lower)
        return (count / max(self.metrics["word_count"], 1)) * 100.0

    async def render(self) -> dict:
        return dict(self.metrics)
