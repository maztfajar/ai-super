"""
Web Search Tool — menggunakan Tavily sebagai provider utama.
Tavily dirancang khusus untuk AI agents, hasilnya sudah
dioptimasi untuk LLM (bersih, terstruktur, ada direct answer).

Free tier: 1.000 query/bulan, tanpa kartu kredit.
Daftar: https://tavily.com
"""
import os
import httpx
import json
import structlog

log = structlog.get_logger()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


async def web_search(query: str, max_results: int = 5) -> str:
    """
    Cari informasi real-time dari internet menggunakan Tavily.
    Dipanggil oleh executor saat model butuh data terkini.
    """
    if not TAVILY_API_KEY:
        log.warning("TAVILY_API_KEY tidak diset, menggunakan Jina fallback")
        return await _jina_fallback(query, max_results)

    return await _tavily_search(query, max_results)


async def _tavily_search(query: str, max_results: int) -> str:
    """Tavily search — hasil dioptimasi untuk LLM."""
    url = "https://api.tavily.com/search"

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",       # "basic" hemat kredit, "advanced" lebih dalam
        "include_answer": True,        # Tavily kadang langsung kasih jawaban ringkas
        "include_raw_content": False,  # True = isi penuh halaman, lebih boros kredit
        "include_images": False,
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()

        lines = [f"🔍 Hasil pencarian real-time: **\"{query}\"**\n"]

        # Tavily sering langsung kasih jawaban singkat — sangat berguna untuk LLM
        if data.get("answer"):
            lines.append(f"📌 **Jawaban langsung:** {data['answer']}\n")

        results = data.get("results", [])
        if not results:
            return f"Tidak ada hasil ditemukan untuk: {query}"

        for i, item in enumerate(results[:max_results], 1):
            title   = item.get("title", "Tanpa judul")
            content = item.get("content", "")[:300]
            url_    = item.get("url", "")
            score   = item.get("score", 0)

            lines.append(
                f"{i}. **{title}**\n"
                f"   {content}\n"
                f"   🔗 {url_}\n"
                f"   (relevance: {score:.2f})\n"
            )

        # Tambahkan timestamp konteks
        import datetime
        now = datetime.datetime.now().strftime("%d %B %Y, %H:%M")
        lines.append(f"\n_Data diambil: {now} WIB_")

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            log.error("Tavily: API key tidak valid atau expired")
            return "❌ API key Tavily tidak valid. Cek TAVILY_API_KEY di .env"
        elif e.response.status_code == 429:
            log.warning("Tavily: rate limit tercapai, coba fallback")
            return await _jina_fallback(query, max_results)
        else:
            log.error("Tavily HTTP error", status=e.response.status_code)
            return f"❌ Error Tavily ({e.response.status_code}): {e.response.text[:100]}"
    except httpx.TimeoutException:
        log.warning("Tavily timeout, menggunakan Jina fallback")
        return await _jina_fallback(query, max_results)
    except Exception as e:
        log.error("Tavily unexpected error", error=str(e)[:100])
        return await _jina_fallback(query, max_results)


async def _jina_fallback(query: str, max_results: int) -> str:
    """
    Fallback gratis jika Tavily tidak tersedia.
    Jina AI: tidak butuh API key sama sekali.
    """
    import urllib.parse
    encoded = urllib.parse.quote(query)
    url = f"https://s.jina.ai/{encoded}"

    headers = {
        "Accept": "application/json",
        "X-Return-Format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()

        # Jina bisa return JSON atau teks
        try:
            data = r.json()
        except Exception:
            return r.text[:1000]

        lines = [f"🔍 Hasil pencarian (Jina fallback): **\"{query}\"**\n"]
        results = data if isinstance(data, list) else data.get("data", [])

        for i, item in enumerate(results[:max_results], 1):
            title   = item.get("title", "")
            content = item.get("content", item.get("description", ""))[:250]
            link    = item.get("url", "")
            lines.append(f"{i}. **{title}**\n   {content}\n   🔗 {link}\n")

        return "\n".join(lines) if len(lines) > 1 else f"Tidak ada hasil untuk: {query}"

    except Exception as e:
        return f"Web search tidak tersedia saat ini: {str(e)[:80]}"


async def web_search_realtime(query: str, max_results: int = 5) -> list:
    """
    Versi yang return list of dict.
    Dipakai orchestrator di Phase 0 untuk inject search context.
    """
    if not TAVILY_API_KEY:
        return [{"title": "Tavily tidak dikonfigurasi", "snippet": "", "url": ""}]

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": True,
        "include_raw_content": False,
        "include_images": False,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()

        results = []

        # Tambahkan direct answer sebagai item pertama jika ada
        if data.get("answer"):
            results.append({
                "title": "Jawaban langsung",
                "snippet": data["answer"],
                "url": "",
            })

        for item in data.get("results", [])[:max_results]:
            results.append({
                "title":   item.get("title", ""),
                "snippet": item.get("content", "")[:200],
                "url":     item.get("url", ""),
            })

        return results

    except Exception as e:
        log.warning("web_search_realtime error", error=str(e)[:80])
        return [{"title": "Error", "snippet": str(e)[:100], "url": ""}]
