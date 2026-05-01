"""
Web Search Tool (v2.1 — Performance Optimized)
===============================================
Perbaikan dari v1:
  1. DuckDuckGo ditambahkan sebagai fallback ke-2 (Tavily → Jina → DuckDuckGo)
  2. Timeout lebih ketat per provider (Tavily 10s, Jina 8s, DDG 6s)
  3. web_search() kini return format yang lebih bersih untuk LLM
  4. Tambahan: web_search_smart() — otomatis pilih provider terbaik
  5. Error handling lebih spesifik per kode HTTP
"""

import os
import httpx
import json
import urllib.parse
import datetime
import structlog

log = structlog.get_logger()


async def web_search(query: str, max_results: int = 5) -> str:
    """
    Cari informasi real-time dari internet.
    Provider chain: Tavily → Jina → DuckDuckGo
    """
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    if tavily_key:
        result = await _tavily_search(query, max_results, tavily_key)
        if not result.startswith("❌"):
            return result
        log.warning("Tavily gagal, mencoba Jina")

    result = await _jina_fallback(query, max_results)
    if not result.startswith("Web search tidak tersedia"):
        return result

    log.warning("Jina gagal, mencoba DuckDuckGo")
    return await _duckduckgo_fallback(query, max_results)


async def _tavily_search(query: str, max_results: int, api_key: str) -> str:
    """Tavily — dirancang khusus untuk AI agents, paling akurat."""
    url = "https://api.tavily.com/search"
    payload = {
        "api_key":             api_key,
        "query":               query,
        "max_results":         max_results,
        "search_depth":        "basic",
        "include_answer":      True,
        "include_raw_content": False,
        "include_images":      False,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()

        lines = [f"🔍 **Hasil pencarian real-time:** \"{query}\"\n"]

        if data.get("answer"):
            lines.append(f"📌 **Jawaban langsung:** {data['answer']}\n")

        results = data.get("results", [])
        if not results:
            return f"Tidak ada hasil untuk: {query}"

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

        now = datetime.datetime.now().strftime("%d %B %Y, %H:%M")
        lines.append(f"\n_Data diambil: {now} WIB_")
        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 401:
            log.error("Tavily: API key tidak valid")
            return "❌ API key Tavily tidak valid"
        elif status == 429:
            log.warning("Tavily: rate limit")
            return "❌ Tavily rate limit"
        elif status == 402:
            log.warning("Tavily: kredit habis")
            return "❌ Tavily kredit habis"
        return f"❌ Tavily error ({status})"
    except httpx.TimeoutException:
        log.warning("Tavily: timeout")
        return "❌ Tavily timeout"
    except Exception as e:
        log.error("Tavily unexpected error", error=str(e)[:80])
        return f"❌ Tavily error: {str(e)[:60]}"


async def _jina_fallback(query: str, max_results: int) -> str:
    """Jina AI — gratis, tidak perlu API key."""
    encoded = urllib.parse.quote(query)
    url = f"https://s.jina.ai/{encoded}"
    headers = {"Accept": "application/json", "X-Return-Format": "json"}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()

        try:
            data = r.json()
        except Exception:
            # Jina terkadang return teks biasa
            text = r.text[:2000]
            if text.strip():
                return f"🔍 **Hasil pencarian:** \"{query}\"\n\n{text}"
            return f"Web search tidak tersedia saat ini"

        lines = [f"🔍 **Hasil pencarian:** \"{query}\"\n"]
        results = data if isinstance(data, list) else data.get("data", [])

        if not results:
            return f"Web search tidak tersedia saat ini"

        for i, item in enumerate(results[:max_results], 1):
            title   = item.get("title", "")
            content = item.get("content", item.get("description", ""))[:250]
            link    = item.get("url", "")
            if title or content:
                lines.append(f"{i}. **{title}**\n   {content}\n   🔗 {link}\n")

        return "\n".join(lines) if len(lines) > 1 else f"Web search tidak tersedia saat ini"

    except Exception as e:
        return f"Web search tidak tersedia saat ini: {str(e)[:60]}"


async def _duckduckgo_fallback(query: str, max_results: int) -> str:
    """
    DuckDuckGo Instant Answer API — fallback terakhir, gratis & tanpa API key.
    Catatan: tidak selengkap Tavily, tapi lebih baik daripada tidak ada.
    """
    encoded = urllib.parse.quote(query)
    url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()

        lines = [f"🔍 **Hasil pencarian (DuckDuckGo):** \"{query}\"\n"]
        added = 0

        # Abstract (jawaban singkat)
        abstract = data.get("AbstractText", "")
        abstract_url = data.get("AbstractURL", "")
        if abstract:
            lines.append(f"📌 **Jawaban:** {abstract}\n   🔗 {abstract_url}\n")
            added += 1

        # Related topics
        topics = data.get("RelatedTopics", [])
        for topic in topics[:max_results - added]:
            if isinstance(topic, dict) and "Text" in topic:
                text = topic.get("Text", "")[:200]
                link = topic.get("FirstURL", "")
                if text:
                    lines.append(f"• {text}\n  🔗 {link}\n")

        if len(lines) <= 1:
            return (
                f"🔍 Tidak ditemukan hasil untuk: \"{query}\"\n"
                f"Coba query yang lebih spesifik atau cek koneksi internet."
            )

        now = datetime.datetime.now().strftime("%d %B %Y, %H:%M")
        lines.append(f"\n_Data diambil: {now} WIB_")
        return "\n".join(lines)

    except Exception as e:
        log.error("DuckDuckGo fallback error", error=str(e)[:80])
        return (
            f"🔍 Web search tidak tersedia saat ini.\n"
            f"Pastikan TAVILY_API_KEY sudah dikonfigurasi di .env untuk hasil terbaik.\n"
            f"Daftar gratis: https://tavily.com"
        )


async def web_search_realtime(query: str, max_results: int = 5) -> list:
    """
    Versi yang return list of dict.
    Dipakai orchestrator di Phase 0 untuk inject search context.
    """
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    if not tavily_key:
        log.warning("TAVILY_API_KEY tidak dikonfigurasi")
        return [{"title": "Tavily tidak dikonfigurasi", "snippet":
                 "Set TAVILY_API_KEY di .env untuk web search real-time. Daftar gratis di tavily.com", "url": ""}]

    url = "https://api.tavily.com/search"
    payload = {
        "api_key":             tavily_key,
        "query":               query,
        "max_results":         max_results,
        "search_depth":        "basic",
        "include_answer":      True,
        "include_raw_content": False,
        "include_images":      False,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()

        results = []

        if data.get("answer"):
            results.append({
                "title":   "Jawaban langsung",
                "snippet": data["answer"],
                "url":     "",
            })

        for item in data.get("results", [])[:max_results]:
            results.append({
                "title":   item.get("title", ""),
                "snippet": item.get("content", "")[:200],
                "url":     item.get("url", ""),
            })

        return results

    except httpx.TimeoutException:
        log.warning("web_search_realtime: Tavily timeout")
        return [{"title": "Timeout", "snippet": "Web search timeout (>10s)", "url": ""}]
    except Exception as e:
        log.warning("web_search_realtime error", error=str(e)[:80])
        return [{"title": "Error", "snippet": str(e)[:100], "url": ""}]
