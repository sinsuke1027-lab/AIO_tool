import httpx
from bs4 import BeautifulSoup
import json
from typing import List, Dict
from .models import ScrapedData

class Scraper:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AIOToolBot/1.0; +http://example.com/bot)"
        }

    async def scrape(self, url: str) -> ScrapedData:
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            html = response.text
            soup = BeautifulSoup(html, "lxml")
            
            # Basic metadata
            title = soup.title.string.strip() if soup.title else ""
            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "").strip()
            
            # H1 tags
            h1s = [h1.get_text().strip() for h1 in soup.find_all("h1")]
            
            # Main content extraction (Simplified for MVP)
            # Remove script and style elements
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()
            
            # Get text and clean up whitespace
            main_text = soup.get_text(separator="\n")
            lines = (line.strip() for line in main_text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            main_text = "\n".join(chunk for chunk in chunks if chunk)
            
            # Limit main text size for LLM context
            main_text = main_text[:10000] 
            
            # Meta tags
            meta_tags = {}
            for meta in soup.find_all("meta"):
                name = meta.get("name") or meta.get("property")
                content = meta.get("content")
                if name and content:
                    meta_tags[name] = content
            
            # JSON-LD
            json_ld = []
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        json_ld.extend(data)
                    else:
                        json_ld.append(data)
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Extract Tables
            tables = []
            for table in soup.find_all("table"):
                table_text = table.get_text(separator=" | ").strip()
                if table_text:
                    tables.append(table_text)

            # Extract Citations / Quotes (Expert voices)
            citations = []
            # Look for blockquotes or elements with 'source' in class
            for quote in soup.find_all(["blockquote", "cite"]):
                txt = quote.get_text().strip()
                if txt:
                    citations.append(txt)
                    
            return ScrapedData(
                url=url,
                title=title,
                description=description,
                h1=h1s,
                main_text=main_text,
                meta_tags=meta_tags,
                json_ld=json_ld,
                tables=tables,
                citations=citations
            )

    async def extract_internal_links(self, url: str, limit: int = 5) -> List[str]:
        from urllib.parse import urljoin, urlparse
        
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")
                
                base_domain = urlparse(url).netloc
                links = set()
                
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full_url = urljoin(url, href)
                    parsed_url = urlparse(full_url)
                    
                    # Same domain, ignore fragments/queries, not the same as root
                    if parsed_url.netloc == base_domain and parsed_url.path and parsed_url.path != "/":
                        clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                        if clean_url != url:
                            links.add(clean_url)
                    
                    if len(links) >= limit:
                        break
                        
                return list(links)
            except Exception:
                return []
