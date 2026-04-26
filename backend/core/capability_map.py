"""
AI ORCHESTRATOR — Capability Map Engine
Automatically discovers and maps AI model capabilities.

Flow:
  startup_sync() → interview each model → store capability tags → expose via API

Capability tags: text, coding, analysis, vision, image_gen, audio, tts,
                 search, reasoning, writing, speed
"""
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Optional, Set
import structlog

log = structlog.get_logger()

# Path untuk menyimpan capability map ke disk
CAPABILITY_MAP_FILE = Path(__file__).parent.parent.parent / "data" / "capability_map.json"

# ── Static capability hints berdasarkan pengetahuan model ─────────────────────
# Digunakan sebagai fallback jika interview LLM gagal, dan sebagai seed awal.
STATIC_CAPABILITY_HINTS: Dict[str, Set[str]] = {
    # Sumopod models
    "mimo-v2-omni":              {"text", "vision", "audio", "reasoning", "analysis"},
    "mimo-v2-pro":               {"text", "reasoning", "coding", "analysis", "writing"},
    "minimax/speech-2.8-hd":     {"audio", "tts"},
    "MiniMax-M2.7-highspeed":    {"text", "writing", "speed"},
    "big-pickle":                {"text", "coding", "analysis"},
    # OpenAI
    "gpt-4o":                    {"text", "vision", "coding", "reasoning", "analysis", "writing"},
    "gpt-4o-mini":               {"text", "coding", "reasoning", "speed"},
    "gpt-image-1":               {"image_gen"},
    "dall-e-3":                  {"image_gen"},
    # Anthropic
    "claude-3-5-sonnet":         {"text", "coding", "reasoning", "analysis", "writing"},
    "claude-3-opus":             {"text", "coding", "reasoning", "analysis"},
    "claude-3-haiku":            {"text", "speed", "writing"},
    # Google
    "gemini-1.5-pro":            {"text", "vision", "reasoning", "analysis"},
    "gemini-1.5-flash":          {"text", "speed", "vision"},
    "gemini-2.0-flash":          {"text", "speed", "vision"},
    "gemini-2.5-pro":            {"text", "vision", "reasoning", "analysis"},
    "gemini-2.5-flash":          {"text", "vision", "speed"},
    # Seed (Sumopod)
    "seed-2-0-pro":              {"text", "reasoning", "coding", "analysis"},
    # Ollama / local
    "llama3":                    {"text", "coding", "reasoning"},
    "llama3.1":                  {"text", "coding", "reasoning"},
    "llama3.2":                  {"text", "reasoning", "speed"},
    "mistral":                   {"text", "coding", "reasoning"},
    "deepseek":                  {"text", "coding", "reasoning"},
    "qwen":                      {"text", "vision", "coding"},
    "llava":                     {"vision", "text"},
    "phi":                       {"text", "coding", "speed"},
    "gemma":                     {"text", "reasoning", "speed"},
}

# Interview prompt — model harus jawab dalam JSON
INTERVIEW_PROMPT = """You are an AI model being asked to describe your capabilities.

Reply ONLY with valid JSON listing your top capabilities from this list:
["text", "coding", "analysis", "vision", "image_gen", "audio", "tts", "search", "reasoning", "writing", "speed"]

Example: {"capabilities": ["text", "reasoning", "coding"]}

Be honest and specific about what you can actually do. Max 5 capabilities."""


class CapabilityMapEngine:
    """
    Manages the discovery and storage of AI model capabilities.
    """

    def __init__(self):
        # In-memory capability map: {model_id: set of capability tags}
        self._map: Dict[str, Set[str]] = {}
        self._last_sync: float = 0.0
        self._sync_interval: int = 1800  # 30 minutes
        self._is_syncing: bool = False

    # ── Public API ──────────────────────────────────────────────────────────

    def get_capabilities(self, model_id: str) -> Set[str]:
        """Get capability tags for a model. Returns empty set if unknown."""
        # Check exact match
        if model_id in self._map:
            return self._map[model_id]
        # Partial match (e.g., "sumopod/mimo-v2-omni" → "mimo-v2-omni")
        for key, caps in self._map.items():
            if key in model_id or model_id in key:
                return caps
        return set()

    def has_capability(self, model_id: str, capability: str) -> bool:
        """Check if a model has a specific capability."""
        return capability in self.get_capabilities(model_id)

    def find_best_model(self, required_capabilities: Set[str],
                        available_models: Dict[str, dict] = None) -> Optional[str]:
        """
        Find the model with the best capability match for the required capabilities.
        Returns model_id or None.
        """
        from core.model_manager import model_manager
        available = available_models or model_manager.available_models
        if not available:
            return None

        best_model = None
        best_score = -1

        for model_id in available:
            model_caps = self.get_capabilities(model_id)
            if not model_caps:
                continue
            overlap = len(model_caps & required_capabilities)
            if overlap > best_score:
                best_score = overlap
                best_model = model_id

        return best_model

    def get_all(self) -> Dict[str, list]:
        """Return the full capability map (sets converted to lists for JSON)."""
        return {model_id: sorted(caps) for model_id, caps in self._map.items()}

    # ── Startup & Background Sync ─────────────────────────────────────────

    async def startup_sync(self):
        """Called at app startup — load from disk then sync new models."""
        self._load_from_disk()
        await self.sync()
        log.info("CapabilityMap startup sync complete", models=len(self._map))

    async def sync(self):
        """
        Sync capability map:
        1. Apply static hints for all known models.
        2. Interview models we've never seen or need refresh.
        3. Persist to disk.
        """
        if self._is_syncing:
            return
        self._is_syncing = True
        start = time.time()

        try:
            from core.model_manager import model_manager
            all_models = model_manager.available_models

            # Step 1: Apply static hints as baseline
            for model_id in all_models:
                if model_id not in self._map:
                    hints = self._match_static_hints(model_id)
                    if hints:
                        self._map[model_id] = hints
                        log.debug("CapabilityMap: static hint applied",
                                  model=model_id, caps=sorted(hints))

            # Step 2: Interview models missing from map (with 5s timeout each)
            interview_tasks = []
            for model_id in all_models:
                if model_id not in self._map:
                    interview_tasks.append(self._interview_model(model_id))

            if interview_tasks:
                results = await asyncio.gather(*interview_tasks, return_exceptions=True)
                log.info(f"CapabilityMap: interviewed {len(interview_tasks)} new models")

            # Step 3: Persist
            self._save_to_disk()
            self._last_sync = time.time()

            elapsed = int((time.time() - start) * 1000)
            log.info("CapabilityMap sync complete",
                     total_models=len(self._map),
                     elapsed_ms=elapsed)

        except Exception as e:
            log.error("CapabilityMap sync error", error=str(e))
        finally:
            self._is_syncing = False

    async def sync_background_loop(self):
        """Background loop that re-syncs every 30 minutes."""
        while True:
            await asyncio.sleep(self._sync_interval)
            log.info("CapabilityMap: background sync triggered")
            await self.sync()

    # ── Model Interview ────────────────────────────────────────────────────

    async def _interview_model(self, model_id: str) -> bool:
        """
        Send a capability interview prompt to a model and store result.
        Returns True if successful.
        """
        try:
            from core.model_manager import model_manager
            messages = [
                {"role": "system", "content": INTERVIEW_PROMPT},
                {"role": "user", "content": "What are your capabilities?"},
            ]
            result = await asyncio.wait_for(
                model_manager.chat_completion(
                    model=model_id,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=100,
                ),
                timeout=8.0,
            )

            # Parse JSON response
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]

            result = result.strip()
            # Find JSON object
            start_idx = result.find("{")
            end_idx = result.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                result = result[start_idx:end_idx]

            data = json.loads(result)
            caps = set(data.get("capabilities", []))

            # Validate against known capability tags
            valid_tags = {"text", "coding", "analysis", "vision", "image_gen",
                          "audio", "tts", "search", "reasoning", "writing", "speed"}
            caps = caps & valid_tags

            if caps:
                self._map[model_id] = caps
                log.info("CapabilityMap: model interviewed",
                         model=model_id, caps=sorted(caps))
                return True

        except asyncio.TimeoutError:
            log.debug("CapabilityMap: interview timeout", model=model_id)
        except Exception as e:
            log.debug("CapabilityMap: interview error", model=model_id, error=str(e)[:80])

        # Fallback: apply static hints if interview fails
        hints = self._match_static_hints(model_id)
        if hints:
            self._map[model_id] = hints
        else:
            self._map[model_id] = {"text"}  # minimal fallback

        return False

    # ── Static Hints Matching ─────────────────────────────────────────────

    def _match_static_hints(self, model_id: str) -> Set[str]:
        """Match model ID against static hints using substring matching."""
        model_lower = model_id.lower()
        matched = set()

        for hint_key, caps in STATIC_CAPABILITY_HINTS.items():
            hint_lower = hint_key.lower()
            if hint_lower in model_lower or model_lower in hint_lower:
                matched |= caps

        # Additional pattern-based hints
        if any(x in model_lower for x in ["vision", "llava", "pixtral", "qwen-vl"]):
            matched.add("vision")
        if any(x in model_lower for x in ["speech", "tts", "voice", "audio"]):
            matched.update({"audio", "tts"})
        if any(x in model_lower for x in ["image", "dalle", "dall-e", "flux", "sdxl"]):
            matched.add("image_gen")
        if any(x in model_lower for x in ["omni", "multimodal", "mm"]):
            matched.update({"vision", "audio", "text"})
        if any(x in model_lower for x in ["flash", "mini", "haiku", "small", "nano"]):
            matched.add("speed")
        if any(x in model_lower for x in ["code", "codex", "coder", "deepseek-coder"]):
            matched.add("coding")

        if not matched:
            matched = {"text"}  # every model can do text by default

        return matched

    # ── Persistence ────────────────────────────────────────────────────────

    def _save_to_disk(self):
        """Persist capability map to JSON file."""
        try:
            CAPABILITY_MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {model_id: sorted(caps) for model_id, caps in self._map.items()}
            CAPABILITY_MAP_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            log.warning("CapabilityMap: failed to save to disk", error=str(e))

    def _load_from_disk(self):
        """Load capability map from disk if exists."""
        try:
            if CAPABILITY_MAP_FILE.exists():
                data = json.loads(CAPABILITY_MAP_FILE.read_text(encoding="utf-8"))
                self._map = {model_id: set(caps) for model_id, caps in data.items()}
                log.info("CapabilityMap: loaded from disk", models=len(self._map))
        except Exception as e:
            log.warning("CapabilityMap: failed to load from disk", error=str(e))


# Global singleton
capability_map = CapabilityMapEngine()
