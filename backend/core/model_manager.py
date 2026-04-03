"""
Model Manager — manages all AI model connections
Supports: OpenAI, Anthropic, Google, Ollama (local), Sumopod (custom OpenAI-compatible)
         + Custom providers (added via UI)
"""
import asyncio
import json
from pathlib import Path
from typing import Optional, AsyncGenerator, Dict
import httpx
import structlog

from core.config import settings

log = structlog.get_logger()

CUSTOM_MODELS_FILE = Path(__file__).parent.parent.parent / ".custom_models.json"


class ModelManager:
    def __init__(self):
        self.available_models: Dict[str, dict] = {}

    async def startup(self):
        await self._detect_models()

    async def shutdown(self):
        pass

    async def _detect_models(self):
        """Detect all available models from API keys and services"""
        self.available_models = {}

        # ── OpenAI ───────────────────────────────────────────
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-..."):
            if settings.OPENAI_AVAILABLE_MODELS:
                for m in settings.OPENAI_AVAILABLE_MODELS.split(","):
                    if m.strip():
                        self.available_models[m.strip()] = {"provider": "openai", "display": f"{m.strip()}", "status": "online"}
            else:
                self.available_models.update({
                    "gpt-4o":       {"provider": "openai", "display": "GPT-4o",       "status": "online"},
                    "gpt-4o-mini":  {"provider": "openai", "display": "GPT-4o Mini",  "status": "online"},
                })
            log.info("OpenAI models registered")

        # ── Anthropic ────────────────────────────────────────
        if settings.ANTHROPIC_API_KEY and not settings.ANTHROPIC_API_KEY.startswith("sk-ant-..."):
            if settings.ANTHROPIC_AVAILABLE_MODELS:
                for m in settings.ANTHROPIC_AVAILABLE_MODELS.split(","):
                    if m.strip():
                        self.available_models[m.strip()] = {"provider": "anthropic", "display": f"{m.strip()}", "status": "online"}
            else:
                self.available_models.update({
                    "claude-3-5-sonnet-20241022": {"provider": "anthropic", "display": "Claude 3.5 Sonnet", "status": "online"},
                    "claude-3-haiku-20240307":    {"provider": "anthropic", "display": "Claude 3 Haiku",    "status": "online"},
                })
            log.info("Anthropic models registered")

        # ── Google ───────────────────────────────────────────
        if settings.GOOGLE_API_KEY and not settings.GOOGLE_API_KEY.startswith("AIza..."):
            if settings.GOOGLE_AVAILABLE_MODELS:
                for m in settings.GOOGLE_AVAILABLE_MODELS.split(","):
                    if m.strip():
                        self.available_models[m.strip()] = {"provider": "google", "display": f"{m.strip()}", "status": "online"}
            else:
                self.available_models.update({
                    "gemini-1.5-pro":   {"provider": "google", "display": "Gemini 1.5 Pro",   "status": "online"},
                    "gemini-1.5-flash": {"provider": "google", "display": "Gemini 1.5 Flash", "status": "online"},
                })
            log.info("Google models registered")

        # ── Sumopod (OpenAI-compatible API) ──────────────────
        if settings.SUMOPOD_API_KEY and not settings.SUMOPOD_API_KEY.startswith("sk-..."):
            for model_id in settings.sumopod_models_list:
                key = f"sumopod/{model_id}"
                self.available_models[key] = {
                    "provider":  "sumopod",
                    "display":   f"{model_id} (Sumopod)",
                    "status":    "online",
                    "model_id":  model_id,
                }
            log.info(f"Sumopod models registered: {settings.sumopod_models_list}")

        # ── Ollama (local) ────────────────────────────────────
        ollama_models = await self._check_ollama()
        self.available_models.update(ollama_models)

        # ── Custom providers (dari UI) ────────────────────────
        custom_models = self._load_custom_models()
        self.available_models.update(custom_models)

        log.info(f"Total models detected: {len(self.available_models)}", models=list(self.available_models.keys()))

    async def _check_ollama(self) -> dict:
        """Check Ollama and list installed models"""
        models = {}

        # Jika user set OLLAMA_AVAILABLE_MODELS di .env, pakai itu dulu
        for m in settings.ollama_models_list:
            clean = m.strip()
            if clean:
                models[f"ollama/{clean}"] = {
                    "provider": "ollama",
                    "display":  f"{clean} (Local)",
                    "status":   "online",
                }

        # Auto-detect dari Ollama API
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{settings.OLLAMA_HOST}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("models", []):
                        name = m["name"]
                        key = f"ollama/{name}"
                        if key not in models:
                            models[key] = {
                                "provider": "ollama",
                                "display":  f"{name} (Local)",
                                "status":   "online",
                            }
                    log.info(f"Ollama auto-detected {len(data.get('models', []))} models")
        except Exception:
            if models:
                log.info(f"Ollama offline, using {len(models)} models from env config")
            else:
                log.info("Ollama not available")

        return models

    def _load_custom_models(self) -> dict:
        """Load custom model providers from .custom_models.json"""
        models = {}
        if not CUSTOM_MODELS_FILE.exists():
            return models
        try:
            providers = json.loads(CUSTOM_MODELS_FILE.read_text(encoding="utf-8"))
            for provider in providers:
                if provider.get("status") not in ("connected", "untested"):
                    continue
                provider_name = provider.get("name", "Custom").strip()
                model_list = [m.strip() for m in provider.get("models", "").split(",") if m.strip()]
                for model_id in model_list:
                    key = f"custom/{provider_name}/{model_id}"
                    models[key] = {
                        "provider": "custom",
                        "display": f"{model_id} ({provider_name})",
                        "status": "online" if provider.get("status") == "connected" else "unknown",
                        "model_id": model_id,
                        "custom_provider_id": provider.get("id"),
                        "base_url": provider.get("base_url", ""),
                        "api_key": provider.get("api_key", ""),
                        "icon": provider.get("icon", "🔌"),
                    }
                if model_list:
                    log.info(f"Custom provider '{provider_name}' loaded: {model_list}")
        except Exception as e:
            log.warning("Failed to load custom models", error=str(e))
        return models

    async def chat_stream(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion — route ke provider yang tepat"""
        provider = self._get_provider(model)
        clean_model = model.replace("sumopod/", "").replace("ollama/", "")

        if provider == "openai":
            async for chunk in self._stream_openai(clean_model, messages, temperature, max_tokens):
                yield chunk
        elif provider == "anthropic":
            async for chunk in self._stream_anthropic(clean_model, messages, temperature, max_tokens):
                yield chunk
        elif provider == "google":
            async for chunk in self._stream_google(clean_model, messages, temperature, max_tokens):
                yield chunk
        elif provider == "sumopod":
            async for chunk in self._stream_openai_compatible(
                clean_model, messages, temperature, max_tokens,
                base_url=settings.SUMOPOD_HOST,
                api_key=settings.SUMOPOD_API_KEY,
                provider_name="Sumopod",
            ):
                yield chunk
        elif provider == "ollama":
            async for chunk in self._stream_ollama(clean_model, messages, temperature, max_tokens):
                yield chunk
        elif provider == "custom":
            info = self.available_models.get(model, {})
            base_url = info.get("base_url", "")
            api_key = info.get("api_key", "")
            actual_model = info.get("model_id", clean_model)
            provider_name = model.split("/")[1] if "/" in model else "Custom"
            if base_url and api_key:
                async for chunk in self._stream_openai_compatible(
                    actual_model, messages, temperature, max_tokens,
                    base_url=base_url, api_key=api_key,
                    provider_name=provider_name,
                ):
                    yield chunk
            else:
                yield f"[Error: Custom provider config tidak lengkap. Cek konfigurasi di Integrasi.]"
        else:
            yield f"[Error: Model '{model}' tidak dikenali. Cek .env kamu.]"

    def _get_provider(self, model: str) -> str:
        """Detect provider dari model ID"""
        if model.startswith("custom/"):
            return "custom"
        if model.startswith("sumopod/"):
            return "sumopod"
        if model.startswith("ollama/"):
            return "ollama"
        info = self.available_models.get(model, {})
        if info.get("provider"):
            return info["provider"]
        # Fallback by name pattern
        if model.startswith("gpt"):
            return "openai"
        if model.startswith("claude"):
            return "anthropic"
        if model.startswith("gemini"):
            return "google"
        if "llama" in model or "mistral" in model or "dolphin" in model:
            return "ollama"
        return "unknown"

    # ── OpenAI ───────────────────────────────────────────────
    async def _stream_openai(self, model, messages, temperature, max_tokens):
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            stream = await client.chat.completions.create(
                model=model, messages=messages,
                temperature=temperature, max_tokens=max_tokens, stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            yield f"\n[Error OpenAI: {e}]"

    # ── Anthropic ─────────────────────────────────────────────
    async def _stream_anthropic(self, model, messages, temperature, max_tokens):
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            system = next((m["content"] for m in messages if m["role"] == "system"), "You are AI SUPER ASSISTANT, a helpful AI assistant.")
            chat_msgs = [m for m in messages if m["role"] != "system"]
            async with client.messages.stream(
                model=model, messages=chat_msgs, system=system,
                temperature=temperature, max_tokens=max_tokens,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            yield f"\n[Error Anthropic: {e}]"

    # ── Google ────────────────────────────────────────────────
    async def _stream_google(self, model, messages, temperature, max_tokens):
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            gmodel = genai.GenerativeModel(model)
            prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
            response = gmodel.generate_content(
                prompt, stream=True,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"\n[Error Google: {e}]"

    # ── OpenAI-compatible (Sumopod, dll) ─────────────────────
    async def _stream_openai_compatible(
        self, model, messages, temperature, max_tokens,
        base_url: str, api_key: str, provider_name: str = "Custom"
    ):
        """
        Generic streaming untuk API yang kompatibel dengan OpenAI format.
        Sumopod, Together AI, Groq, dsb semua pakai format ini.
        """
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            yield f"\n[Error {provider_name}: {e}]"

    # ── Ollama ────────────────────────────────────────────────
    async def _stream_ollama(self, model, messages, temperature, max_tokens):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{settings.OLLAMA_HOST}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": True,
                        "options": {"temperature": temperature, "num_predict": max_tokens},
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
        except Exception as e:
            yield f"\n[Error Ollama: {e}. Pastikan Ollama berjalan: ollama serve]"

    # ── Status & utils ────────────────────────────────────────
    async def get_status(self) -> list:
        return [
            {"id": mid, **info}
            for mid, info in self.available_models.items()
        ]

    def get_default_model(self) -> str:
        if self.available_models:
            return list(self.available_models.keys())[0]
        return settings.DEFAULT_MODEL


model_manager = ModelManager()
