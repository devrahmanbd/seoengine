"""
HTTP Client Service - Real page fetching with retry logic
"""

import asyncio
import aiohttp
from typing import Dict, Optional, Any
from bs4 import BeautifulSoup
import re


class FetchResult:
    def __init__(self, success: bool, html: str = "", status_code: int = 0, 
                 error: str = "", headers: Dict = None, response_time: float = 0):
        self.success = success
        self.html = html
        self.status_code = status_code
        self.error = error
        self.headers = headers or {}
        self.response_time = response_time


class HTTPClient:
    """Async HTTP client with retries and proper timeout handling"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def fetch(self, url: str, user_agent: str = None) -> FetchResult:
        """Fetch a URL with retry logic"""
        if not user_agent:
            user_agent = "Mozilla/5.0 (compatible; ZenSEO/1.0; +https://zenseo.ai)"
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        for attempt in range(self.max_retries):
            try:
                import time
                start_time = time.time()
                
                async with self.session.get(url, headers=headers, 
                                           allow_redirects=True) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        html = await response.text()
                        return FetchResult(
                            success=True,
                            html=html,
                            status_code=response.status,
                            headers=dict(response.headers),
                            response_time=response_time
                        )
                    else:
                        return FetchResult(
                            success=False,
                            status_code=response.status,
                            error=f"HTTP {response.status}"
                        )
                        
            except asyncio.TimeoutError:
                if attempt == self.max_retries - 1:
                    return FetchResult(success=False, error="Timeout after retries")
            except aiohttp.ClientError as e:
                if attempt == self.max_retries - 1:
                    return FetchResult(success=False, error=str(e))
            
            await asyncio.sleep(0.5 * (attempt + 1))
        
        return FetchResult(success=False, error="Max retries exceeded")
    
    async def fetch_with_headers(self, url: str) -> Dict[str, Any]:
        """Fetch page and extract important SEO headers"""
        result = await self.fetch(url)
        
        if not result.success:
            return {"error": result.error, "success": False}
        
        soup = BeautifulSoup(result.html, 'html.parser')
        
        extracted = {
            "success": True,
            "url": url,
            "status_code": result.status_code,
            "response_time": result.response_time,
            "headers": result.headers,
            
            # Meta tags
            "title": soup.title.string if soup.title else None,
            "meta_description": soup.find("meta", {"name": "description"})["content"] 
                              if soup.find("meta", {"name": "description"}) else None,
            "meta_robots": soup.find("meta", {"name": "robots"})["content"] 
                          if soup.find("meta", {"name": "robots"}) else None,
            "canonical": soup.find("link", {"rel": "canonical"})["href"] 
                        if soup.find("link", {"rel": "canonical"}) else None,
            
            # Open Graph
            "og_title": soup.find("meta", {"property": "og:title"})["content"] 
                       if soup.find("meta", {"property": "og:title"}) else None,
            "og_description": soup.find("meta", {"property": "og:description"})["content"] 
                            if soup.find("meta", {"property": "og:description"}) else None,
            "og_image": soup.find("meta", {"property": "og:image"})["content"] 
                      if soup.find("meta", {"property": "og:image"}) else None,
            
            # H1 tags
            "h1_tags": [h.get_text(strip=True) for h in soup.find_all("h1")],
            "h2_tags": [h.get_text(strip=True) for h in soup.find_all("h2")],
            
            # Links
            "internal_links": [],
            "external_links": [],
            
            # Images
            "images": [],
            "images_without_alt": [],
            
            # Scripts/Styles
            "scripts": len(soup.find_all("script")),
            "stylesheets": len(soup.find_all("link", {"rel": "stylesheet"})),
            
            # Body text
            "body_text": soup.get_text(separator=" ", strip=True)[:10000],
            "html": result.html
        }
        
        # Extract links
        base_domain = url.split("/")[2] if "://" in url else ""
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("/") or base_domain in href:
                extracted["internal_links"].append(href)
            elif href.startswith("http"):
                extracted["external_links"].append(href)
        
        # Extract images
        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "")
            if src:
                extracted["images"].append({"src": src, "alt": alt})
                if not alt:
                    extracted["images_without_alt"].append(src)
        
        # Schema.org structured data
        scripts = soup.find_all("script", {"type": "application/ld+json"})
        extracted["json_ld_scripts"] = [s.string for s in scripts if s.string]
        
        # HTTP headers of interest
        extracted["x_robots"] = result.headers.get("x-robots-tag", "")
        
        return extracted


async def fetch_page(url: str) -> Dict[str, Any]:
    """Convenience function to fetch a page"""
    async with HTTPClient() as client:
        return await client.fetch_with_headers(url)