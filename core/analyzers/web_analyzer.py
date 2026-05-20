"""
Web Analyzer - Fetches and analyzes websites
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
import re


class WebAnalyzer:
    """Analyzes websites for SEO metrics"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; ZenSEO-Bot/2.0)"
        })
        self.timeout = 30
    
    async def fetch_page(self, url: str) -> Dict[str, Any]:
        """Fetch and parse a web page"""
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            return {
                "url": url,
                "status_code": response.status_code,
                "title": self._get_title(soup),
                "meta": self._get_meta(soup),
                "headings": self._get_headings(soup),
                "links": self._get_links(soup, url),
                "images": self._get_images(soup),
                "content": self._get_content(soup),
                "schema": self._get_schema(soup),
                "scripts": self._get_scripts(soup),
                "word_count": len(self._get_content(soup).split()),
                "load_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            return {"error": str(e), "url": url}
    
    def _get_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        title = soup.find("title")
        if title:
            return title.text.strip()
        
        h1 = soup.find("h1")
        if h1:
            return h1.text.strip()
        
        return ""
    
    def _get_meta(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract meta tags"""
        meta = {}
        
        # Description
        desc = soup.find("meta", {"name": "description"})
        if desc:
            meta["description"] = desc.get("content", "")
        
        # Open Graph
        og_title = soup.find("meta", {"property": "og:title"})
        if og_title:
            meta["og_title"] = og_title.get("content", "")
        
        og_desc = soup.find("meta", {"property": "og:description"})
        if og_desc:
            meta["og_description"] = og_desc.get("content", "")
        
        og_image = soup.find("meta", {"property": "og:image"})
        if og_image:
            meta["og_image"] = og_image.get("content", "")
        
        # Robots
        robots = soup.find("meta", {"name": "robots"})
        if robots:
            meta["robots"] = robots.get("content", "")
        
        # Canonical
        canonical = soup.find("link", {"rel": "canonical"})
        if canonical:
            meta["canonical"] = canonical.get("href", "")
        
        return meta
    
    def _get_headings(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract all headings"""
        headings = []
        
        for level in range(1, 7):
            for heading in soup.find_all(f"h{level}"):
                text = heading.get_text(strip=True)
                if text:
                    headings.append({
                        "level": level,
                        "text": text
                    })
        
        return headings
    
    def _get_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, List]:
        """Extract all links"""
        links = {"internal": [], "external": [], "total": 0}
        
        base_domain = urlparse(base_url).netloc
        
        for link in soup.find_all("a", href=True):
            href = link.get("href")
            
            # Skip anchors and javascript
            if href.startswith("#") or href.startswith("javascript:"):
                continue
            
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            
            link_info = {
                "url": full_url,
                "text": link.get_text(strip=True)[:50],
                "is_follow": link.get("rel") != "nofollow"
            }
            
            if parsed.netloc == base_domain or parsed.netloc == "":
                links["internal"].append(link_info)
            else:
                links["external"].append(link_info)
        
        links["total"] = len(links["internal"]) + len(links["external"])
        return links
    
    def _get_images(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract all images"""
        images = []
        
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            alt = img.get("alt", "")
            
            if src:
                images.append({
                    "src": src,
                    "alt": alt,
                    "has_alt": bool(alt)
                })
        
        return images
    
    def _get_content(self, soup: BeautifulSoup) -> str:
        """Extract main content"""
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Try to find main content areas
        main = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile("content|article|post", re.I))
        
        if main:
            return main.get_text(separator=" ", strip=True)
        
        return soup.get_text(separator=" ", strip=True)
    
    def _get_schema(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract JSON-LD schema"""
        schemas = []
        
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string)
                schemas.append(data)
            except:
                pass
        
        return schemas
    
    def _get_scripts(self, soup: BeautifulSoup) -> List[str]:
        """Extract external script URLs"""
        scripts = []
        
        for script in soup.find_all("script", src=True):
            src = script.get("src")
            if src:
                scripts.append(src)
        
        return scripts
    
    async def analyze_competitors(
        self,
        target_url: str,
        competitor_urls: List[str]
    ) -> Dict[str, Any]:
        """Analyze competitors compared to target"""
        
        target_data = await self.fetch_page(target_url)
        
        competitors = []
        for url in competitor_urls:
            data = await self.fetch_page(url)
            competitors.append(data)
        
        # Compare metrics
        comparison = {
            "target": {
                "word_count": target_data.get("word_count", 0),
                "headings_count": len(target_data.get("headings", [])),
                "images_count": len(target_data.get("images", [])),
                "internal_links": len(target_data.get("links", {}).get("internal", [])),
                "schema_count": len(target_data.get("schema", []))
            },
            "competitors": [],
            "gaps": [],
            "opportunities": []
        }
        
        # Calculate competitor averages
        if competitors:
            avg_words = sum(c.get("word_count", 0) for c in competitors) / len(competitors)
            target_words = comparison["target"]["word_count"]
            
            if target_words < avg_words * 0.8:
                comparison["gaps"].append(f"Content length below average ({target_words} vs {int(avg_words)})")
            
            for comp in competitors:
                comparison["competitors"].append({
                    "url": comp.get("url", ""),
                    "word_count": comp.get("word_count", 0),
                    "headings": len(comp.get("headings", [])),
                    "has_schema": len(comp.get("schema", [])) > 0
                })
        
        return comparison


class ContentAuditor:
    """Deep content audit with scoring"""
    
    def __init__(self):
        self.web_analyzer = WebAnalyzer()
    
    async def audit(
        self,
        content: str,
        title: str,
        meta_description: str,
        headings: List[Dict],
        keyword: str
    ) -> Dict[str, Any]:
        """Basic content audit"""
        
        # Title analysis
        title_analysis = self._audit_title(title, keyword)
        
        # Meta analysis
        meta_analysis = self._audit_meta(meta_description, keyword)
        
        # Heading analysis
        heading_analysis = self._audit_headings(headings, keyword)
        
        # Content analysis
        content_analysis = self._audit_content(content, keyword)
        
        # Calculate scores
        technical_score = (title_analysis["score"] * 0.4 + 
                          meta_analysis["score"] * 0.3 + 
                          heading_analysis["score"] * 0.3)
        
        return {
            "title_analysis": title_analysis,
            "meta_analysis": meta_analysis,
            "heading_analysis": heading_analysis,
            "content_analysis": content_analysis,
            "score": int(technical_score),
            "issues": (title_analysis["issues"] + 
                      meta_analysis["issues"] + 
                      content_analysis["issues"])
        }
    
    async def deep_audit(
        self,
        url: str,
        content: str,
        keyword: str,
        content_type: str
    ) -> Dict[str, Any]:
        """Comprehensive content audit"""
        
        if url:
            page_data = await self.web_analyzer.fetch_page(url)
            content = content or page_data.get("content", "")
            title = page_data.get("title", "")
            meta = page_data.get("meta", {}).get("description", "")
            headings = page_data.get("headings", [])
        else:
            title = ""
            meta = ""
            headings = []
        
        # Basic audit
        basic = await self.audit(content, title, meta, headings, keyword)
        
        # Readability analysis
        readability = self._analyze_readability(content)
        
        # Structure analysis
        structure = self._analyze_structure(headings, content)
        
        # E-E-A-T analysis
        eeat = self._analyze_eeat(content, keyword)
        
        # Calculate final scores
        final_score = (
            basic["score"] * 0.25 +
            readability["score"] * 0.25 +
            structure["score"] * 0.25 +
            eeat["score"] * 0.25
        )
        
        return {
            "url": url,
            "score": int(final_score),
            "readability_score": readability["score"],
            "structure_score": structure["score"],
            "content_score": basic.get("content_analysis", {}).get("score", 50),
            "eeat_score": eeat["score"],
            "issues": basic["issues"],
            "recommendations": self._generate_recommendations(
                basic, readability, structure, eeat
            ),
            "timestamp": datetime.now().isoformat()
        }
    
    def _audit_title(self, title: str, keyword: str) -> Dict:
        score = 50
        issues = []
        
        if not title:
            issues.append("Missing title tag")
            score -= 30
        else:
            if len(title) < 30:
                issues.append("Title too short (<30 chars)")
                score -= 10
            elif len(title) > 60:
                issues.append("Title too long (>60 chars)")
                score -= 10
            
            if keyword and keyword.lower() in title.lower():
                score += 25
            elif keyword:
                issues.append("Keyword not in title")
                score -= 15
        
        return {"score": max(0, min(100, score)), "issues": issues, "length": len(title)}
    
    def _audit_meta(self, meta: str, keyword: str) -> Dict:
        score = 50
        issues = []
        
        if not meta:
            issues.append("Missing meta description")
            score -= 25
        else:
            if len(meta) < 120:
                issues.append("Meta too short (<120 chars)")
                score -= 10
            elif len(meta) > 160:
                issues.append("Meta too long (>160 chars)")
                score -= 10
            
            if keyword and keyword.lower() in meta.lower():
                score += 20
        
        return {"score": max(0, min(100, score)), "issues": issues, "length": len(meta)}
    
    def _audit_headings(self, headings: List[Dict], keyword: str) -> Dict:
        score = 60
        issues = []
        
        h1_count = sum(1 for h in headings if h.get("level") == 1)
        
        if h1_count == 0:
            issues.append("No H1 heading")
            score -= 20
        elif h1_count > 1:
            issues.append("Multiple H1 headings")
            score -= 10
        
        has_keyword = any(
            keyword.lower() in h.get("text", "").lower() 
            for h in headings 
            if h.get("level") in [2, 3]
        )
        
        if has_keyword:
            score += 20
        
        return {
            "score": max(0, min(100, score)),
            "issues": issues,
            "h1_count": h1_count,
            "total_headings": len(headings)
        }
    
    def _audit_content(self, content: str, keyword: str) -> Dict:
        score = 50
        issues = []
        
        word_count = len(content.split())
        
        if word_count < 300:
            issues.append(f"Content too short ({word_count} words)")
            score -= 15
        elif word_count > 300:
            score += 15
        
        if keyword:
            density = content.lower().count(keyword.lower()) / max(1, word_count) * 100
            
            if 1 <= density <= 2.5:
                score += 20
            elif density > 3:
                issues.append("Keyword stuffing")
                score -= 15
            elif density < 0.5:
                issues.append("Low keyword density")
                score -= 10
        
        return {"score": max(0, min(100, score)), "issues": issues, "word_count": word_count}
    
    def _analyze_readability(self, content: str) -> Dict:
        """Analyze readability metrics"""
        words = content.split()
        sentences = content.split(".") + content.split("!") + content.split("?")
        
        avg_word_len = sum(len(w) for w in words) / max(1, len(words))
        avg_sent_len = len(words) / max(1, len(sentences))
        
        # Simple Flesch approximation
        score = 100 - (avg_sent_len * 0.5) - (avg_word_len * 2)
        
        return {"score": max(0, min(100, int(score))), "avg_sentence_length": avg_sent_len}
    
    def _analyze_structure(self, headings: List[Dict], content: str) -> Dict:
        """Analyze content structure"""
        score = 50
        
        if len(headings) >= 3:
            score += 20
        
        if content.split("\n\n") >= 3:
            score += 15
        
        return {"score": max(0, min(100, score)), "heading_count": len(headings)}
    
    def _analyze_eeat(self, content: str, keyword: str) -> Dict:
        """Analyze E-E-A-T signals"""
        score = 50
        
        # Experience indicators
        exp_words = ["we", "our", "I have", "my experience", "years", "tested", "worked"]
        experience_count = sum(1 for w in exp_words if w in content.lower())
        
        # Expertise indicators
        expert_words = ["research", "study", "data", "analysis", "expert", "proven"]
        expertise_count = sum(1 for w in expert_words if w in content.lower())
        
        score += min(25, experience_count * 5)
        score += min(25, expertise_count * 5)
        
        return {"score": max(0, min(100, score)), "experience_signals": experience_count}
    
    def _generate_recommendations(self, basic, readability, structure, eeat) -> List[str]:
        """Generate actionable recommendations"""
        recs = []
        
        if basic["title_analysis"]["issues"]:
            recs.append("Fix title tag issues")
        if basic["meta_analysis"]["issues"]:
            recs.append("Optimize meta description")
        if readability["score"] < 60:
            recs.append("Improve readability with shorter sentences")
        if structure["score"] < 70:
            recs.append("Add more subheadings to improve structure")
        if eeat["score"] < 60:
            recs.append("Add more E-E-A-T signals (experience, expertise)")
        
        return recs[:5]


from datetime import datetime