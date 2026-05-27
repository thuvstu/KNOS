# backend/app/services/import_pipeline/url_scraper.py
import httpx
import structlog
from dataclasses import dataclass
from typing import Optional

logger = structlog.get_logger()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.9",
}


@dataclass
class ScrapeResult:
    url: str
    title: str
    content: str
    author: Optional[str] = None
    domain: str = ""


async def scrape_url(url: str) -> Optional[ScrapeResult]:
    """段階的フォールバックでURLをスクレイプ"""

    # Step 1: httpx + trafilatura
    result = await _scrape_trafilatura(url)
    if result:
        return result

    logger.warning("scraper_fallback", url=url, failed_scraper="trafilatura", next_scraper="curl_cffi")

    # Step 2: curl_cffi (TLS偽装)
    result = await _scrape_curl_cffi(url)
    if result:
        return result

    logger.warning("scraper_fallback", url=url, failed_scraper="curl_cffi", next_scraper="None")
    return None


async def _scrape_trafilatura(url: str) -> Optional[ScrapeResult]:
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        try:
            import trafilatura
            content = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
            metadata = trafilatura.extract_metadata(html)
            title = (metadata.title if metadata else None) or _extract_title(html) or url
            author = metadata.author if metadata else None
        except ImportError:
            # trafilatura非インストール時はHTMLから簡易抽出
            content = _simple_extract(html)
            title = _extract_title(html) or url
            author = None

        if not content:
            return None

        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "")

        logger.info("scrape_success", url=url, scraper="trafilatura", title=title[:50])
        return ScrapeResult(url=url, title=title, content=content, author=author, domain=domain)

    except Exception as e:
        logger.warning("scrape_failed", url=url, scraper="trafilatura", error=str(e))
        return None


async def _scrape_curl_cffi(url: str) -> Optional[ScrapeResult]:
    try:
        from curl_cffi.requests import AsyncSession
        async with AsyncSession() as session:
            response = await session.get(url, impersonate="chrome124", timeout=20)
            html = response.text

        try:
            import trafilatura
            content = trafilatura.extract(html) or ""
            metadata = trafilatura.extract_metadata(html)
            title = (metadata.title if metadata else None) or _extract_title(html) or url
            author = metadata.author if metadata else None
        except ImportError:
            content = _simple_extract(html)
            title = _extract_title(html) or url
            author = None

        if not content:
            return None

        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "")

        logger.info("scrape_success", url=url, scraper="curl_cffi", title=title[:50])
        return ScrapeResult(url=url, title=title, content=content, author=author, domain=domain)

    except ImportError:
        logger.warning("curl_cffi_not_installed")
        return None
    except Exception as e:
        logger.warning("scrape_failed", url=url, scraper="curl_cffi", error=str(e))
        return None


def _extract_title(html: str) -> Optional[str]:
    import re
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _simple_extract(html: str) -> str:
    import re
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()[:5000]
