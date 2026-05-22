import re
import time
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from app.atropos.base_env import SEOEnvironment, SEOAction, State


class _TechHTMLParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.base_netloc = urlparse(base_url).netloc
        self.title_text = ""
        self.meta_description = None
        self.h1_count = 0
        self.schema_tags = []
        self.internal_links = []
        self.external_links = []
        self.images = []
        self.canonical = None
        self.og_tags = {}
        self.viewport = None
        self._in_title = False
        self._in_schema = False
        self._schema_depth = 0
        self._title_parts = []

    def handle_starttag(self, tag, attrs):
        attrs_map = dict(attrs)
        t = tag.lower()
        if t == "title":
            self._in_title = True
        elif t == "meta":
            name = attrs_map.get("name", "").lower()
            prop = attrs_map.get("property", "").lower()
            content = attrs_map.get("content", "")
            if name == "description":
                self.meta_description = content
            elif name == "viewport":
                self.viewport = content
            if prop == "og:title":
                self.og_tags["og:title"] = content
            elif prop == "og:description":
                self.og_tags["og:description"] = content
            elif prop == "og:image":
                self.og_tags["og:image"] = content
        elif t == "h1":
            self.h1_count += 1
        elif t == "a":
            href = attrs_map.get("href", "")
            if href and not href.startswith("#") and not href.startswith("javascript:"):
                parsed = urlparse(href)
                if parsed.netloc and parsed.netloc != self.base_netloc:
                    self.external_links.append(href)
                elif href.startswith("/") or not parsed.netloc:
                    self.internal_links.append(href)
        elif t == "img":
            src = attrs_map.get("src", "")
            alt = attrs_map.get("alt", "")
            self.images.append({"src": src, "alt": alt})
        elif t == "link":
            rel = attrs_map.get("rel", "")
            if isinstance(rel, str):
                rel = rel.lower()
            if rel == "canonical":
                self.canonical = attrs_map.get("href", "")
        elif t == "script":
            script_type = attrs_map.get("type", "")
            if "ld+json" in script_type:
                self._in_schema = True
                self._schema_depth = 0
        if self._in_schema:
            self._schema_depth += 1

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == "title":
            self._in_title = False
            self.title_text = "".join(self._title_parts).strip()
            self._title_parts = []
        if self._in_schema:
            self._schema_depth -= 1
            if self._schema_depth <= 0:
                self._in_schema = False
                self.schema_tags.append(True)

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)


class TechnicalSEOEnv(SEOEnvironment):
    WEIGHTS = {
        "status_code": 0.15,
        "title_length": 0.10,
        "meta_description_length": 0.10,
        "h1_count": 0.12,
        "has_schema": 0.10,
        "images_missing_alt_ratio": 0.10,
        "has_canonical": 0.08,
        "has_og_tags": 0.05,
        "has_viewport": 0.05,
        "response_time_ms": 0.10,
        "internal_links_score": 0.025,
        "external_links_score": 0.025,
    }

    def __init__(self, site_id: str, max_steps: int = 10):
        self.site_id = site_id
        self.max_steps = max_steps
        self.current_step = 0
        self.metrics = self._default_metrics()
        self._html = ""
        self._parser = None
        self._page_fetched = False

    def _default_metrics(self) -> dict:
        return {
            "status_code": 0,
            "title": "",
            "title_length": 0,
            "meta_description": "",
            "meta_description_length": 0,
            "h1_count": 0,
            "schema_count": 0,
            "internal_links": 0,
            "external_links": 0,
            "images_total": 0,
            "images_missing_alt": 0,
            "has_canonical": False,
            "og_title": False,
            "og_description": False,
            "og_image": False,
            "has_viewport": False,
            "response_time_ms": 0.0,
            "technical_score": 0.0,
        }

    async def reset(self) -> State:
        self.current_step = 0
        await self._fetch_and_parse()
        score = self._compute_score(self.metrics)
        self.metrics["technical_score"] = score
        return State(
            site_id=self.site_id,
            metrics=dict(self.metrics),
            timestamp=time.time(),
            features=[score],
        )

    async def _fetch_and_parse(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                start = time.perf_counter()
                resp = await client.get(self.site_id)
                elapsed = time.perf_counter() - start
                self.metrics["status_code"] = resp.status_code
                self.metrics["response_time_ms"] = round(elapsed * 1000, 1)
                self._html = resp.text
        except Exception:
            self.metrics["status_code"] = 0
            self.metrics["response_time_ms"] = 99999.0
            self._html = ""
            return
        if not self._html:
            return
        parser = _TechHTMLParser(self.site_id)
        try:
            parser.feed(self._html)
        except Exception:
            pass
        self._parser = parser
        self.metrics["title"] = parser.title_text
        self.metrics["title_length"] = len(parser.title_text)
        self.metrics["meta_description"] = parser.meta_description or ""
        self.metrics["meta_description_length"] = len(parser.meta_description or "")
        self.metrics["h1_count"] = parser.h1_count
        self.metrics["schema_count"] = len(parser.schema_tags)
        self.metrics["internal_links"] = len(parser.internal_links)
        self.metrics["external_links"] = len(parser.external_links)
        self.metrics["images_total"] = len(parser.images)
        self.metrics["images_missing_alt"] = sum(
            1 for img in parser.images if not img["alt"].strip()
        )
        self.metrics["has_canonical"] = parser.canonical is not None
        self.metrics["og_title"] = "og:title" in parser.og_tags
        self.metrics["og_description"] = "og:description" in parser.og_tags
        self.metrics["og_image"] = "og:image" in parser.og_tags
        self.metrics["has_viewport"] = parser.viewport is not None
        self._page_fetched = True

    def _compute_score(self, metrics: dict) -> float:
        scores = {}
        sc = metrics.get("status_code", 0)
        if sc == 200:
            scores["status_code"] = 1.0
        elif sc == 301:
            scores["status_code"] = 0.7
        elif sc == 302:
            scores["status_code"] = 0.6
        elif sc == 404 or sc == 410:
            scores["status_code"] = 0.0
        elif sc >= 500:
            scores["status_code"] = 0.0
        elif sc == 0:
            scores["status_code"] = 0.0
        else:
            scores["status_code"] = 0.3

        tlen = metrics.get("title_length", 0)
        if 50 <= tlen <= 60:
            scores["title_length"] = 1.0
        elif 30 <= tlen < 50 or 60 < tlen <= 70:
            scores["title_length"] = 0.8
        elif 15 <= tlen < 30 or 70 < tlen <= 100:
            scores["title_length"] = 0.5
        elif tlen == 0:
            scores["title_length"] = 0.0
        else:
            scores["title_length"] = 0.2

        mlen = metrics.get("meta_description_length", 0)
        if 150 <= mlen <= 160:
            scores["meta_description_length"] = 1.0
        elif 120 <= mlen < 150 or 160 < mlen <= 200:
            scores["meta_description_length"] = 0.8
        elif 50 <= mlen < 120 or 200 < mlen <= 300:
            scores["meta_description_length"] = 0.5
        elif mlen == 0:
            scores["meta_description_length"] = 0.0
        else:
            scores["meta_description_length"] = 0.2

        h1 = metrics.get("h1_count", 0)
        if h1 == 1:
            scores["h1_count"] = 1.0
        elif h1 == 0:
            scores["h1_count"] = 0.0
        else:
            scores["h1_count"] = 0.5

        scores["has_schema"] = 1.0 if metrics.get("schema_count", 0) > 0 else 0.0

        img_total = metrics.get("images_total", 0)
        img_missing = metrics.get("images_missing_alt", 0)
        if img_total > 0:
            scores["images_missing_alt_ratio"] = 1.0 - (img_missing / img_total)
        else:
            scores["images_missing_alt_ratio"] = 1.0

        scores["has_canonical"] = 1.0 if metrics.get("has_canonical") else 0.0

        og_count = sum([
            1 if metrics.get("og_title") else 0,
            1 if metrics.get("og_description") else 0,
            1 if metrics.get("og_image") else 0,
        ])
        scores["has_og_tags"] = og_count / 3.0

        scores["has_viewport"] = 1.0 if metrics.get("has_viewport") else 0.0

        rt = metrics.get("response_time_ms", 99999)
        if rt < 200:
            scores["response_time_ms"] = 1.0
        elif rt < 500:
            scores["response_time_ms"] = 0.8
        elif rt < 1000:
            scores["response_time_ms"] = 0.5
        elif rt < 3000:
            scores["response_time_ms"] = 0.2
        else:
            scores["response_time_ms"] = 0.0

        internal = metrics.get("internal_links", 0)
        if internal >= 10:
            scores["internal_links_score"] = 1.0
        elif internal >= 5:
            scores["internal_links_score"] = 0.8
        elif internal >= 1:
            scores["internal_links_score"] = 0.6
        else:
            scores["internal_links_score"] = 0.0

        external = metrics.get("external_links", 0)
        if 1 <= external <= 10:
            scores["external_links_score"] = 1.0
        elif external > 10:
            scores["external_links_score"] = 0.7
        else:
            scores["external_links_score"] = 0.0

        total = sum(
            scores.get(key, 0.0) * weight
            for key, weight in self.WEIGHTS.items()
        )
        return min(max(total, 0.0), 1.0)

    async def step(self, action: SEOAction) -> tuple[State, float, bool, dict]:
        self.current_step += 1
        old_score = self.metrics.get("technical_score", 0.0)
        action_result = {"applied": False, "message": "Unknown action"}

        if action.action_type == "fix_title":
            new_title = action.params.get("title", "")
            if new_title:
                self.metrics["title"] = new_title
                self.metrics["title_length"] = len(new_title)
                action_result = {"applied": True, "message": "Title updated"}
            else:
                action_result = {"applied": False, "message": "No title provided"}

        elif action.action_type == "fix_meta":
            new_meta = action.params.get("description", "")
            if new_meta:
                self.metrics["meta_description"] = new_meta
                self.metrics["meta_description_length"] = len(new_meta)
                action_result = {"applied": True, "message": "Meta description updated"}
            else:
                action_result = {"applied": False, "message": "No description provided"}

        elif action.action_type == "add_schema":
            schema_type = action.params.get("schema_type", "Organization")
            if self.metrics["schema_count"] == 0:
                self.metrics["schema_count"] = 1
                action_result = {"applied": True, "message": f"Schema {schema_type} added"}
            else:
                action_result = {"applied": True, "message": f"Schema {schema_type} added (additional)"}
                self.metrics["schema_count"] += 1

        elif action.action_type == "fix_headings":
            target_count = action.params.get("h1_count", 1)
            if self.metrics["h1_count"] != 1:
                old_h1 = self.metrics["h1_count"]
                self.metrics["h1_count"] = min(max(target_count, 1), 1)
                action_result = {
                    "applied": True,
                    "message": f"Headings normalized from {old_h1} to 1 H1",
                }
            else:
                action_result = {"applied": True, "message": "Already has one H1"}

        elif action.action_type == "fix_images":
            total = self.metrics["images_total"]
            missing = self.metrics["images_missing_alt"]
            if missing > 0 and total > 0:
                self.metrics["images_missing_alt"] = 0
                action_result = {
                    "applied": True,
                    "message": f"Alt text added to {missing} images",
                }
            elif total == 0:
                action_result = {"applied": True, "message": "No images to fix"}
            else:
                action_result = {"applied": True, "message": "All images already have alt text"}

        elif action.action_type == "improve_cwv":
            suggestions = action.params.get("suggestions", [])
            self.metrics["response_time_ms"] = max(
                self.metrics["response_time_ms"] * 0.6, 50.0
            )
            action_result = {
                "applied": True,
                "message": f"CWV improvements applied: {suggestions}" if suggestions else "CWV improvements applied",
            }

        new_score = self._compute_score(self.metrics)
        self.metrics["technical_score"] = new_score
        reward = max(min(new_score - old_score, 1.0), -1.0)

        done = new_score > 0.85 or self.current_step >= self.max_steps

        info = {
            "action_result": action_result,
            "new_metrics": dict(self.metrics),
            "score_delta": reward,
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

    async def render(self) -> dict:
        return dict(self.metrics)
