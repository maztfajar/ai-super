import aiohttp
import json

async def web_search(query: str) -> str:
    """Perform a web search using DuckDuckGo Instant Answer API and return a concise summary.
    The API returns JSON; we extract the Abstract if available, otherwise the first RelatedTopic.
    """
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return f"Error: DuckDuckGo returned status {resp.status}"
                data = await resp.json()
                # Prefer abstract
                abstract = data.get("Abstract")
                if abstract:
                    return abstract.strip()
                # Fallback to first related topic description
                related = data.get("RelatedTopics")
                if isinstance(related, list) and related:
                    first = related[0]
                    if isinstance(first, dict):
                        return first.get("Text", "No result").strip()
                return "No relevant result found."
    except Exception as e:
        return f"Error performing web search: {str(e)}"
