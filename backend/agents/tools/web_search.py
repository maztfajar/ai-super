"""
AI SUPER ASSISTANT — Web Search Tool (Upgraded)
Multi-engine web search with real-time results support.
"""
import asyncio
from typing import List
import structlog

log = structlog.get_logger()

async def web_search(query: str, max_results: int = 5) -> str:
    """
    Perform web search and return formatted text results.
    Primary entry point called by the agent executor.
    """
    results = await web_search_realtime(query, max_results=max_results)
    if not results:
        # If it fails, give the AI a hint to retry with different keywords
        return f"Tidak ada hasil ditemukan untuk: {query}. (Silakan coba kata kunci lain atau persingkat kueri)"

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
    Search mechanism using duckduckgo_search library.
    Each result: {"title": str, "snippet": str, "url": str, "source": str}
    """
    results = []
    
    try:
        from duckduckgo_search import DDGS
        def do_ddgs():
            res = []
            # We use DDGS context manager and text search
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results, region='id-id'):
                    res.append({
                        "title": r.get('title', ''),
                        "snippet": r.get('body', ''),
                        "url": r.get('href', ''),
                        "source": "duckduckgo_search"
                    })
            return res
            
        # Run synchronous network operation in thread pool to avoid blocking async loop
        results = await asyncio.to_thread(do_ddgs)
        if results:
            log.info("WebSearch: DDGS success", query=query[:50], count=len(results))
            return results
    except ImportError:
        log.error("WebSearch: duckduckgo_search library not installed! Run: pip install duckduckgo-search httpx")
    except Exception as e:
        log.warning("WebSearch: DDGS failed", error=str(e)[:80])
        
    # Provide a simple fallback relying on a very basic Wikipedia search if DDGS fails
    if query.lower().startswith("siapa") or query.lower().startswith("apa"):
        try:
            import httpx
            from urllib.parse import quote
            url = f"https://id.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote(query)}&utf8=&format=json"
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("query", {}).get("search", [])[:max_results]:
                        import re
                        snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
                        results.append({
                            "title": item.get("title", ""),
                            "snippet": snippet,
                            "url": f"https://id.wikipedia.org/wiki/{quote(item.get('title', ''))}",
                            "source": "wikipedia"
                        })
            if results:
                log.info("WebSearch: Wikipedia fallback used successfully")
                return results
        except Exception as e:
            log.warning("WebSearch: Wikipedia fallback failed", error=str(e)[:80])

    return []
