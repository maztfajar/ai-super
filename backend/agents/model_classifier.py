"""
AI ORCHESTRATOR — Dynamic Model Classifier
===========================================
Secara otomatis menentukan kemampuan setiap model AI yang terdaftar
dan membangun routing cache untuk agent_registry.

Alur:
  1. Coba keyword matching dari MODEL_ROLE_HINTS (offline, cepat)
  2. Jika model tidak dikenal → cari diam-diam di internet via Tavily/httpx
  3. Simpan hasil di cache lokal (.model_capabilities_cache.json)
  4. Rebuild routing saat startup & setiap kali model baru didaftarkan
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Set
import structlog

log = structlog.get_logger()

CACHE_FILE = Path(__file__).parent.parent.parent / ".model_capabilities_cache.json"

# ── Keyword → capability tags ─────────────────────────────────────────────────
# Urutan dict penting: kunci spesifik (haiku, sonnet) lebih dahulu dari umum (claude)
MODEL_ROLE_HINTS: Dict[str, List[str]] = {
    # ── AI Core Models ──────────────────────────────
    "claude-haiku-4-5":      ["writing", "creative", "formatting", "speed"],
    "gemini-2.5-flash":      ["speed", "vision", "reasoning", "text"],
    "gpt-5-mini":            ["speed", "reasoning", "vision", "coding"],
    "deepseek-v4-pro":       ["reasoning", "coding", "analysis"],
    "qwen3.6-plus":          ["coding", "reasoning", "speed", "vision", "writing"],
    "speech-2.8-hd":         ["audio", "tts"],

    # ── Generic speed/size keywords ─────────────────
    "flash":   ["speed", "text"],
    "lite":    ["speed", "free"],
    "mini":    ["speed"],
    "turbo":   ["speed"],
    "nano":    ["speed", "free"],

    # ── Generic quality keywords ─────────────────────
    "pro":    ["reasoning", "analysis"],
    "plus":   ["reasoning", "writing"],
    "ultra":  ["reasoning", "analysis"],
    "large":  ["reasoning", "analysis"],

    # ── Special capability keywords ──────────────────
    "vision":  ["vision"],
    "embed":   ["embedding"],
    "coder":   ["coding"],
}

# ── Agent role → required capability tags ─────────────────────────────────────
ROLE_REQUIREMENTS: Dict[str, List[str]] = {
    "general":    ["speed", "free", "text"],
    "writing":    ["writing", "creative", "formatting"],
    "creative":   ["creative", "writing"],
    "research":   ["speed", "text", "vision"],
    "coding":     ["coding"],
    "reasoning":  ["reasoning", "analysis"],
    "system":     ["coding", "reasoning"],
    "validation": ["reasoning", "analysis"],
    "vision":     ["vision"],
    "multimodal": ["vision"],
    "audio_gen":  ["audio", "tts"],
    "image_gen":  ["vision"],
}

# ── In-memory routing cache ────────────────────────────────────────────────────
# { agent_type → [ordered list of model keys] }
_routing_cache: Dict[str, List[str]] = {}
_classified_cache: Dict[str, Set[str]] = {}  # model_key → set of tags
_cache_lock = asyncio.Lock()


# ── Load / Save disk cache ────────────────────────────────────────────────────

def _load_disk_cache() -> Dict[str, List[str]]:
    """Load capability cache dari disk (list disimpan sebagai list)."""
    if not CACHE_FILE.exists():
        return {}
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return {k: list(v) for k, v in data.items()}
    except Exception:
        return {}


def _save_disk_cache(cache: Dict[str, List[str]]):
    """Simpan capability cache ke disk."""
    try:
        CACHE_FILE.write_text(
            json.dumps({k: list(v) for k, v in cache.items()},
                       indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        log.warning("model_classifier: disk cache save failed", error=str(e)[:60])


# ── Keyword matching ──────────────────────────────────────────────────────────

def _keyword_classify(model_key: str) -> Set[str]:
    """
    Ambil capability tags dari nama model via keyword matching.
    Kembalikan set kosong jika tidak ada hint yang cocok.
    """
    # Normalisasi: buang prefix provider (sumopod/, ollama/, custom/...)
    name = model_key.lower()
    for prefix in ("sumopod/", "ollama/", "openai/", "anthropic/", "google/", "custom/"):
        name = name.replace(prefix, "")

    tags: Set[str] = set()
    # Coba match dari yang paling spesifik (panjang) ke yang umum (pendek)
    sorted_hints = sorted(MODEL_ROLE_HINTS.keys(), key=len, reverse=True)
    for keyword in sorted_hints:
        if keyword in name:
            tags.update(MODEL_ROLE_HINTS[keyword])
            # Jika sudah match keyword panjang & spesifik, bisa break
            # Tapi biarkan akumulasi agar dapat semua tag relevan
    return tags


# ── Silent web search untuk model tidak dikenal ───────────────────────────────

async def _search_model_capabilities(model_name: str) -> Set[str]:
    """
    Cari diam-diam di internet: model ini jago di bidang apa?
    Gunakan Tavily jika tersedia, fallback ke httpx + DuckDuckGo.
    """
    clean_name = model_name.replace("sumopod/", "").replace("ollama/", "")
    query = f"{clean_name} AI model capabilities strengths use cases benchmark"
    tags: Set[str] = set()

    try:
        # Coba Tavily dulu
        from core.config import settings
        if settings.TAVILY_API_KEY and not settings.TAVILY_API_KEY.startswith("tvly-..."):
            import httpx
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": query,
                        "search_depth": "basic",
                        "max_results": 3,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = " ".join(
                        r.get("content", "") for r in data.get("results", [])
                    ).lower()
                    tags = _parse_capability_from_text(content, clean_name)
                    if tags:
                        log.info("model_classifier: web search result",
                                 model=clean_name, tags=list(tags))
                        return tags
    except Exception as e:
        log.debug("model_classifier: Tavily search failed", error=str(e)[:60])

    # Fallback: DuckDuckGo instant answer (tanpa API key)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=6) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                abstract = (data.get("AbstractText", "") + " " +
                            " ".join(t.get("Text", "") for t in data.get("RelatedTopics", []))).lower()
                tags = _parse_capability_from_text(abstract, clean_name)
    except Exception as e:
        log.debug("model_classifier: DuckDuckGo fallback failed", error=str(e)[:60])

    return tags


def _parse_capability_from_text(text: str, model_name: str) -> Set[str]:
    """Ekstrak capability tags dari teks deskripsi model."""
    tags: Set[str] = set()
    # Keyword mapping untuk deteksi dari teks natural
    text_hints = {
        "cod":        "coding",    # coding, code, coder
        "programm":   "coding",
        "debug":      "coding",
        "math":       "reasoning",
        "logic":      "reasoning",
        "reason":     "reasoning",
        "analys":     "analysis",
        "research":   "analysis",
        "write":      "writing",
        "writ":       "writing",
        "creat":      "creative",
        "story":      "creative",
        "fast":       "speed",
        "quick":      "speed",
        "vision":     "vision",
        "image":      "vision",
        "multimodal": "vision",
        "audio":      "audio",
        "speech":     "audio",
        "transcri":   "audio",
        "free":       "free",
        "cheap":      "free",
        "format":     "formatting",
        "markdown":   "formatting",
    }
    for keyword, tag in text_hints.items():
        if keyword in text:
            tags.add(tag)

    # Default: jika tidak ada yang cocok, tambahkan text
    if not tags:
        tags.add("text")
    return tags


# ── Score model untuk sebuah agent role ──────────────────────────────────────

def _score_model_for_role(model_tags: Set[str], role: str) -> float:
    """
    Hitung skor model untuk agent role tertentu.
    Semakin tinggi skor, semakin cocok model untuk role ini.
    """
    required = set(ROLE_REQUIREMENTS.get(role, ["text"]))
    if not required:
        return 0.0

    # Bonus per tag yang match
    match_count = len(model_tags & required)
    base_score = match_count / max(len(required), 1)

    # Bonus khusus
    bonus = 0.0
    if "free" in model_tags and role in ("general", "research", "writing", "creative"):
        bonus += 0.3  # model gratis sangat diutamakan untuk tugas ringan
    if "speed" in model_tags and role in ("general", "research"):
        bonus += 0.2
    if "coding" in model_tags and role in ("coding", "system"):
        bonus += 0.2
    if "reasoning" in model_tags and role in ("reasoning", "validation"):
        bonus += 0.2
    if "writing" in model_tags and role in ("writing", "creative"):
        bonus += 0.2
    if "audio" in model_tags and role == "audio_gen":
        bonus += 0.5
    if "vision" in model_tags and role in ("vision", "multimodal", "image_gen"):
        bonus += 0.3

    # Penalti: model audio jangan masuk non-audio role
    if "audio" in model_tags and "tts" in model_tags and role not in ("audio_gen",):
        return -1.0

    # Penalti: model embedding jangan masuk chat role
    if "embedding" in model_tags:
        return -1.0

    return base_score + bonus


# ── Main: rebuild routing cache ───────────────────────────────────────────────

async def rebuild_routing_cache(available_models: Dict[str, dict]):
    """
    Bangun ulang routing cache berdasarkan model yang terdaftar.
    Dipanggil saat startup & saat model baru didaftarkan di Integrasi.
    """
    global _routing_cache, _classified_cache

    if not available_models:
        return

    # Load disk cache untuk model yang sudah pernah diclassify
    disk_cache = _load_disk_cache()

    # Classify setiap model
    classified: Dict[str, Set[str]] = {}
    search_tasks = []

    for model_key in available_models:
        if model_key in disk_cache:
            # Cache hit — pakai hasil sebelumnya
            classified[model_key] = set(disk_cache[model_key])
        else:
            # Keyword matching dulu
            tags = _keyword_classify(model_key)
            if tags:
                classified[model_key] = tags
                disk_cache[model_key] = list(tags)
                log.debug("model_classifier: keyword classified",
                          model=model_key, tags=list(tags))
            else:
                # Jadwalkan web search untuk model tidak dikenal
                search_tasks.append(model_key)

    # Jalankan web search secara paralel untuk model tidak dikenal
    if search_tasks:
        log.info("model_classifier: searching capabilities for unknown models",
                 models=search_tasks)
        results = await asyncio.gather(
            *[_search_model_capabilities(m) for m in search_tasks],
            return_exceptions=True
        )
        for model_key, result in zip(search_tasks, results):
            if isinstance(result, Exception) or not result:
                # Fallback: taruh di "text" agar tetap tersedia
                tags = {"text", "speed"}
            else:
                tags = result
            classified[model_key] = tags
            disk_cache[model_key] = list(tags)
            log.info("model_classifier: web search classified",
                     model=model_key, tags=list(tags))

    # Simpan cache ke disk
    _save_disk_cache(disk_cache)

    # Build routing: untuk setiap role, urutkan model berdasarkan skor
    new_routing: Dict[str, List[str]] = {}
    all_roles = list(ROLE_REQUIREMENTS.keys())

    for role in all_roles:
        scored = []
        for model_key, tags in classified.items():
            score = _score_model_for_role(tags, role)
            if score > 0:
                scored.append((model_key, score))
        # Urutkan: skor tertinggi dulu
        scored.sort(key=lambda x: x[1], reverse=True)
        new_routing[role] = [m for m, _ in scored]

    async with _cache_lock:
        _routing_cache = new_routing
        _classified_cache = classified

    # Log ringkasan routing
    for role, models in new_routing.items():
        if models:
            log.info(f"model_classifier: [{role}] → {models[:3]}")

    log.info("model_classifier: routing cache rebuilt",
             total_models=len(classified),
             roles=len(new_routing))


# ── Get routing untuk agent ────────────────────────────────────────────────────

def get_preferred_models(agent_type: str) -> List[str]:
    """
    Ambil ordered list model terbaik untuk agent_type.
    Dipanggil oleh agent_registry.resolve_model_for_agent().
    Kembalikan list kosong jika cache belum dibangun.
    """
    return list(_routing_cache.get(agent_type, []))


def get_model_tags(model_key: str) -> Set[str]:
    """Ambil capability tags dari sebuah model."""
    return set(_classified_cache.get(model_key, set()))


def is_cache_ready() -> bool:
    """Cek apakah routing cache sudah dibangun."""
    return bool(_routing_cache)
