"""
AI SUPER ASSISTANT — Web Search Tool (Upgraded)
Multi-engine web search with real-time results support.

Engines (in priority order):
  1. DuckDuckGo HTML scraping (structured results, no API key needed)
  2. SearXNG public instances (fallback)
  3. DuckDuckGo Instant Answer API (last resort)
"""
import asyncio
import json
import re
from typing import List, Optional
import structlog

log = structlog.get_logger()

# Public SearXNG instances as fallback
SEARXNG_INSTANCES = [
    "https://searx.be",
    "https://search.bus-hit.me",
    "https://searxng.world",
]


async def web_search(query: str, max_results: int = 5) -> str:
    """
    Perform web search and return formatted text results.
    Primary entry point called by the agent executor.
    """
    results = await web_search_realtime(query, max_results=max_results)
    if not results:
        return f"Tidak ada hasil ditemukan untuk: {query}"

    lines = [f"🔍 Hasil pencarian untuk: **{query}**\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        if r.get("snippet"):
            lines.append(f"   {r['snippet']}")
        if r.get("url"):
            lines.append(f"   🔗 {r['url']}")
        lines.append("")

    return "\n".join(lines)


async def web_search_realtime(query: str, max_results: int = 5) -> List[dict]:
    """
    Multi-engine search returning structured result list.
    Each result: {"title": str, "snippet": str, "url": str, "source": str}
    """
    # Try DuckDuckGo HTML first
    try:
        results = await asyncio.wait_for(
            _search_duckduckgo_html(query, max_results),
            timeout=12.0,
        )
        if results:
            log.info("WebSearch: DuckDuckGo HTML success", query=query[:50], count=len(results))
            return results
    except Exception as e:
        log.debug("WebSearch: DuckDuckGo HTML failed", error=str(e)[:80])

    # Try SearXNG fallback
    for instance in SEARXNG_INSTANCES:
        try:
            results = await asyncio.wait_for(
                _search_searxng(instance, query, max_results),
                timeout=10.0,
            )
            if results:
                log.info("WebSearch: SearXNG success", instance=instance, count=len(results))
                return results
        except Exception as e:
            log.debug("WebSearch: SearXNG failed", instance=instance, error=str(e)[:60])
            continue

    # Last resort: DuckDuckGo Instant Answer API
    try:
        results = await asyncio.wait_for(
            _search_duckduckgo_api(query),
            timeout=8.0,
        )
        if results:
            log.info("WebSearch: DuckDuckGo API fallback success", query=query[:50])
            return results
    except Exception as e:
        log.debug("WebSearch: DuckDuckGo API failed", error=str(e)[:80])

    return []


async def _search_duckduckgo_html(query: str, max_results: int = 5) -> List[dict]:
    """Scrape DuckDuckGo HTML search results."""
    import httpx
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    url = "https://html.duckduckgo.com/html/"
    params = {"q": query, "kl": "id-id"}

    async with httpx.AsyncClient(timeout=12, headers=headers, follow_redirects=True) as client:
        resp = await client.post(url, data=params)
        if resp.status_code != 200:
            return []

    html = resp.text
    results = []

    # Extract results using regex (no heavy HTML parser needed)
    # Pattern for result blocks: title, url, snippet
    result_blocks = re.findall(
        r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>.*?'
        r'<a[^>]+class="result__snippet"[^>]*>([^<]*(?:<[^/][^>]*>[^<]*</[^>]+>)*[^<]*)</a>',
        html, re.DOTALL
    )

    for url_raw, title_raw, snippet_raw in result_blocks[:max_results]:
        # Clean up HTML tags from snippet
        snippet = re.sub(r"<[^>]+>", "", snippet_raw).strip()
        title = re.sub(r"<[^>]+>", "", title_raw).strip()
        # Decode HTML entities
        for entity, char in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                              ("&quot;", '"'), ("&#x27;", "'"), ("&nbsp;", " ")]:
            title = title.replace(entity, char)
            snippet = snippet.replace(entity, char)

        if title and snippet:
            results.append({
                "title": title,
                "snippet": snippet[:300],
                "url": url_raw,
                "source": "duckduckgo",
            })

    # Fallback: simpler extraction if regex didn't match
    if not results:
        title_matches = re.findall(r'class="result__a"[^>]*>([^<]+)</a>', html)
        snippet_matches = re.findall(r'class="result__snippet"[^>]*>([^<]+)</a>', html)
        url_matches = re.findall(r'class="result__a"[^>]*href="([^"]+)"', html)

        for i in range(min(len(title_matches), len(snippet_matches), max_results)):
            title = title_matches[i].strip()
            snippet = snippet_matches[i].strip()
            url = url_matches[i] if i < len(url_matches) else ""
            if title:
                results.append({
                    "title": title,
                    "snippet": snippet[:300],
                    "url": url,
                    "source": "duckduckgo",
                })

    return results


async def _search_searxng(instance: str, query: str, max_results: int = 5) -> List[dict]:
    """Search using a public SearXNG instance (JSON API)."""
    import httpx
    url = f"{instance}/search"
    params = {
        "q": query,
        "format": "json",
        "categories": "general",
        "language": "id",
        "time_range": "",
        "safesearch": "0",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AI-Assistant/1.0)",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=10, headers=headers, follow_redirects=True) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return []

    data = resp.json()
    raw_results = data.get("results", [])
    results = []

    for item in raw_results[:max_results]:
        title = item.get("title", "").strip()
        snippet = item.get("content", "").strip()
        url = item.get("url", "")
        if title:
            results.append({
                "title": title,
                "snippet": snippet[:300],
                "url": url,
                "source": f"searxng:{instance}",
            })

    return results


async def _search_duckduckgo_api(query: str) -> List[dict]:
    """DuckDuckGo Instant Answer API (last resort, often no results for news)."""
    import httpx
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"

    async with httpx.AsyncClient(timeout=8) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return []

    data = resp.json()
    results = []

    # Abstract
    abstract = data.get("Abstract", "").strip()
    abstract_url = data.get("AbstractURL", "")
    if abstract:
        results.append({
            "title": data.get("Heading", query),
            "snippet": abstract[:300],
            "url": abstract_url,
            "source": "duckduckgo_api",
        })

    # Related topics
    for item in data.get("RelatedTopics", [])[:4]:
        if isinstance(item, dict) and item.get("Text"):
            results.append({
                "title": item.get("Text", "")[:80],
                "snippet": item.get("Text", "")[:300],
                "url": item.get("FirstURL", ""),
                "source": "duckduckgo_api",
            })

    return results
