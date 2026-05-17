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
        # Singleton HTTP clients — dibuat sekali, direuse setiap request
        self._openai_client = None
        self._anthropic_client = None

    async def startup(self):
        await self._detect_models()
        await self._init_clients()

    async def _init_clients(self):
        """Initialize singleton API clients."""
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-..."):
            try:
                from openai import AsyncOpenAI
                self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                log.info("OpenAI client (singleton) initialized")
            except Exception as e:
                log.warning("Failed to init OpenAI client", error=str(e)[:80])

        if settings.ANTHROPIC_API_KEY and not settings.ANTHROPIC_API_KEY.startswith("sk-ant-..."):
            try:
                import anthropic
                self._anthropic_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                log.info("Anthropic client (singleton) initialized")
            except Exception as e:
                log.warning("Failed to init Anthropic client", error=str(e)[:80])

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
                    "gpt-5-mini": {"provider": "openai", "display": "GPT-5 Mini", "status": "online"},
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
                    "claude-haiku-4-5": {"provider": "anthropic", "display": "Claude Haiku 4.5", "status": "online"},
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
                    "gemini-2.5-flash": {"provider": "google", "display": "Gemini 2.5 Flash", "status": "online"},
                })
            log.info("Google models registered")

        # ── Sumopod (OpenAI-compatible API) ──────────────────
        if settings.SUMOPOD_API_KEY and not settings.SUMOPOD_API_KEY.startswith("sk-..."):
            # Tambahkan model dari .env (manual override) dulu
            env_models = settings.sumopod_models_list
            for model_id in env_models:
                key = f"sumopod/{model_id}"
                self.available_models[key] = {
                    "provider":  "sumopod",
                    "display":   f"{model_id} (Sumopod)",
                    "status":    "online",
                    "model_id":  model_id,
                }
            
            # Auto-detect dari endpoint /models hanya jika list manual kosong
            if not env_models:
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.get(
                            f"{settings.SUMOPOD_HOST}/models",
                            headers={"Authorization": f"Bearer {settings.SUMOPOD_API_KEY}"}
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            detected = 0
                            for m in data.get("data", []):
                                model_id = m.get("id")
                                if model_id:
                                    key = f"sumopod/{model_id}"
                                    if key not in self.available_models:
                                        self.available_models[key] = {
                                            "provider":  "sumopod",
                                            "display":   f"{model_id} (Sumopod)",
                                            "status":    "online",
                                            "model_id":  model_id,
                                        }
                                        detected += 1
                            if detected > 0:
                                log.info(f"Sumopod auto-detected {detected} additional models")
                except Exception as e:
                    log.warning("Sumopod /models auto-detect failed", error=str(e)[:80])

            log.info(f"Sumopod models registered: {[k for k in self.available_models.keys() if k.startswith('sumopod/')]}")

        # ── Ollama (local) ────────────────────────────────────
        ollama_models = await self._check_ollama()
        self.available_models.update(ollama_models)

        # ── Custom providers (dari UI) ────────────────────────
        custom_models = self._load_custom_models()
        self.available_models.update(custom_models)

        log.info(f"Total models detected: {len(self.available_models)}", models=list(self.available_models.keys()))

        # ── Rebuild dynamic routing cache (diam-diam di background) ─────────
        try:
            from agents.model_classifier import rebuild_routing_cache
            import asyncio
            asyncio.create_task(rebuild_routing_cache(self.available_models))
        except Exception as e:
            log.debug("model_classifier: rebuild skipped", reason=str(e)[:60])

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

    async def chat_completion(self, model: str, messages: list, temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """Helper to get a full text response instead of a stream for internal logic."""
        full = []
        async for chunk in self.chat_stream(model, messages, temperature, max_tokens):
            full.append(chunk)
        return "".join(full)

    async def test_model_tool_support(self, model: str) -> dict:
        """Test if a given model supports native tool calling."""
        provider = self._get_provider(model)
        clean_model = model.replace("sumopod/", "").replace("ollama/", "")
        
        messages = [{"role": "user", "content": "Ping."}]
        dummy_tools = [{
            "type": "function",
            "function": {
                "name": "ping_tool",
                "description": "Dummy tool.",
                "parameters": {"type": "object", "properties": {}}
            }
        }]
        
        try:
            if provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                await client.chat.completions.create(
                    model=clean_model, messages=messages, max_tokens=10, tools=dummy_tools, stream=False
                )
            elif provider == "anthropic":
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                dummy_tools_anthropic = [{
                    "name": "ping_tool",
                    "description": "Dummy tool.",
                    "input_schema": {"type": "object", "properties": {}}
                }]
                await client.messages.create(
                    model=clean_model, messages=messages, max_tokens=10, tools=dummy_tools_anthropic
                )
            elif provider == "google":
                import google.generativeai as genai
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                gmodel = genai.GenerativeModel(
                    clean_model,
                    tools=[{"function_declarations": [{"name": "ping_tool", "description": "dummy"}]}]
                )
                import asyncio
                await asyncio.get_event_loop().run_in_executor(None, lambda: gmodel.generate_content("Ping."))
            elif provider in ("sumopod", "custom"):
                info = self.available_models.get(model, {})
                base_url = info.get("base_url", settings.SUMOPOD_HOST)
                api_key = info.get("api_key", settings.SUMOPOD_API_KEY)
                actual_model = info.get("model_id", clean_model)
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                await client.chat.completions.create(
                    model=actual_model, messages=messages, max_tokens=10, tools=dummy_tools, stream=False
                )
            elif provider == "ollama":
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        f"{settings.OLLAMA_HOST}/api/chat",
                        json={"model": clean_model, "messages": messages, "stream": False, "tools": dummy_tools}
                    )
                    if resp.status_code >= 400:
                        raise Exception(resp.text)
            else:
                return {"supported": False, "message": "Provider tidak didukung untuk pengujian tool."}
                
            return {"supported": True, "message": "Model ini mendukung Native Tools!"}
            
        except Exception as e:
            err_str = str(e).lower()
            if "tool" in err_str or "function" in err_str or "400" in err_str:
                return {"supported": False, "message": f"Model TIDAK mendukung Native Tools: {e}"}
            return {"supported": False, "message": f"Tidak dapat memverifikasi dukungan tools (Error: {e})"}

    async def chat_stream(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list = None,
    ) -> AsyncGenerator[str | dict, None]:
        """Stream chat completion — route ke provider yang tepat"""
        provider = self._get_provider(model)
        clean_model = model.replace("sumopod/", "").replace("ollama/", "")

        if provider == "openai":
            async for chunk in self._stream_openai(clean_model, messages, temperature, max_tokens, tools):
                yield chunk
        elif provider == "anthropic":
            async for chunk in self._stream_anthropic(clean_model, messages, temperature, max_tokens, tools):
                yield chunk
        elif provider == "google":
            async for chunk in self._stream_google(clean_model, messages, temperature, max_tokens, tools):
                yield chunk
        elif provider == "sumopod":
            async for chunk in self._stream_openai_compatible(
                clean_model, messages, temperature, max_tokens,
                base_url=settings.SUMOPOD_HOST,
                api_key=settings.SUMOPOD_API_KEY,
                provider_name="Sumopod",
                tools=tools,
            ):
                yield chunk
        elif provider == "ollama":
            async for chunk in self._stream_ollama(clean_model, messages, temperature, max_tokens, tools):
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
    async def _stream_openai(self, model, messages, temperature, max_tokens, tools=None):
        try:
            # Gunakan singleton client — bukan dibuat ulang tiap request
            if self._openai_client is None:
                from openai import AsyncOpenAI
                self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                
            kwargs = {}
            if tools:
                kwargs["tools"] = tools
                
            stream = await self._openai_client.chat.completions.create(
                model=model, messages=messages,
                temperature=temperature, max_tokens=max_tokens, stream=True,
                **kwargs
            )
            
            tool_calls_buffer = {}
            
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {"name": tc.function.name or "", "args": tc.function.arguments or ""}
                        else:
                            if tc.function.name:
                                tool_calls_buffer[idx]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_buffer[idx]["args"] += tc.function.arguments
                                
            for idx, tc in tool_calls_buffer.items():
                try:
                    import json
                    args_dict = json.loads(tc["args"])
                except:
                    args_dict = tc["args"]
                yield {"type": "tool_call", "name": tc["name"], "args": args_dict}
                
        except Exception as e:
            err_str = str(e)
            if "overdue balance" in err_str.lower() or "insufficient_quota" in err_str.lower():
                yield "\n❌ API Key OpenAI Anda kehabisan saldo (Overdue Balance / Insufficient Quota). Silakan isi ulang saldo / ganti API Key di menu Integrations untuk melanjutkan."
            elif "401" in err_str or "unauthorized" in err_str.lower() or "invalid_api_key" in err_str.lower():
                yield "\n❌ API Key OpenAI Anda tidak valid (401 Unauthorized). Silakan periksa kembali API Key di menu Integrasi."
            else:
                import re
                clean_err = re.sub(r"Error code: \d+ - ", "", err_str).strip()
                if clean_err.startswith("{"):
                    try:
                        import json
                        err_json = json.loads(clean_err.replace("'", '"'))
                        if "error" in err_json and "message" in err_json["error"]:
                            clean_err = err_json["error"]["message"]
                    except:
                        pass
                yield f"\n❌ **Gagal menghubungi OpenAI:** {clean_err}"

    # ── Anthropic ─────────────────────────────────────────────
    async def _stream_anthropic(self, model, messages, temperature, max_tokens, tools=None):
        try:
            # Gunakan singleton client
            if self._anthropic_client is None:
                import anthropic
                self._anthropic_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            system_parts = [m["content"] for m in messages if m["role"] == "system"]
            system = "\n\n".join(system_parts) if system_parts else "You are AI ORCHESTRATOR, a helpful AI assistant."
            chat_msgs = [m for m in messages if m["role"] != "system"]
            
            kwargs = {}
            if tools:
                from core.tool_converter import openai_to_anthropic_tools
                kwargs["tools"] = openai_to_anthropic_tools(tools)
                
            async with self._anthropic_client.messages.stream(
                model=model, messages=chat_msgs, system=system,
                temperature=temperature, max_tokens=max_tokens,
                **kwargs
            ) as stream:
                tool_calls_buffer = {}
                async for event in stream:
                    if event.type == "text_delta":
                        yield event.delta.text
                    elif event.type == "tool_use":
                        # Not streamed delta, tool_use gives the whole JSON usually, 
                        # but anthropic's stream actually sends tool_use block and delta
                        pass
                
                # In Anthropic's messages.stream, tool use blocks are collected automatically
                message = await stream.get_final_message()
                for block in message.content:
                    if block.type == "tool_use":
                        yield {"type": "tool_call", "name": block.name, "args": block.input}
                        
        except Exception as e:
            err_str = str(e)
            if "credit balance is too low" in err_str.lower() or "insufficient_quota" in err_str.lower():
                 yield "\n❌ Saldo API Key Anthropic Anda tidak mencukupi. Silakan isi ulang saldo di Console Anthropic."
            elif "401" in err_str or "unauthorized" in err_str.lower() or "invalid_api_key" in err_str.lower():
                 yield "\n❌ API Key Anthropic Anda tidak valid (401 Unauthorized). Silakan periksa kembali API Key di menu Integrasi."
            else:
                 import re
                 clean_err = re.sub(r"Error code: \d+ - ", "", err_str).strip()
                 yield f"\n❌ **Gagal menghubungi Anthropic:** {clean_err}"

    # ── Google ────────────────────────────────────────────────
    async def _stream_google(self, model, messages, temperature, max_tokens, tools=None):
        """
        Google Gemini streaming dengan format prompt yang benar.
        Dijalankan di thread pool agar tidak memblokir event loop (SDK sync).
        """
        try:
            import asyncio
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)

            # Pisahkan system prompt dari history percakapan
            system_parts = [m["content"] for m in messages if m["role"] == "system"]
            system_instruction = "\n\n".join(system_parts) if system_parts else None
            
            kwargs = {}
            if tools:
                from core.tool_converter import openai_to_gemini_tools
                gemini_tools = openai_to_gemini_tools(tools)
                if gemini_tools:
                    kwargs["tools"] = gemini_tools

            # Buat model dengan system instruction
            gmodel = genai.GenerativeModel(
                model,
                system_instruction=system_instruction,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
                **kwargs
            )

            # Konversi history ke format Gemini (hanya role user/model)
            history = []
            chat_messages = [m for m in messages if m["role"] != "system"]
            for i, m in enumerate(chat_messages[:-1]):
                role = "user" if m["role"] == "user" else "model"
                history.append({"role": role, "parts": [m["content"]]})

            # Pesan terakhir dari user
            last_msg = chat_messages[-1]["content"] if chat_messages else ""

            # Jalankan di thread pool — SDK Gemini bersifat synchronous
            loop = asyncio.get_event_loop()

            def _generate_sync():
                chat = gmodel.start_chat(history=history)
                return chat.send_message(last_msg, stream=False)

            response = await loop.run_in_executor(None, _generate_sync)
            
            if response.parts:
                for part in response.parts:
                    if getattr(part, 'function_call', None):
                        # Convert protobuf struct to dict
                        fn = part.function_call
                        args = {k: v for k, v in type(fn.args).items(fn.args)}
                        yield {"type": "tool_call", "name": fn.name, "args": args}
                    elif part.text:
                        yield part.text
            else:
                yield response.text or ""

        except Exception as e:
            err_str = str(e)
            if "API_KEY_INVALID" in err_str or "401" in err_str:
                yield "\n❌ API Key Google Anda tidak valid. Silakan periksa kembali di menu Integrasi."
            elif "QUOTA_EXCEEDED" in err_str or "429" in err_str:
                yield "\n❌ Kuota Google API Anda telah habis. Silakan coba beberapa saat lagi."
            elif "SAFETY" in err_str:
                yield "\n❌ Respons diblokir oleh filter keamanan Google Gemini."
            else:
                yield f"\n❌ **Gagal menghubungi Google Gemini:** {str(e)[:200]}"

    async def _stream_openai_compatible(
        self, model, messages, temperature, max_tokens,
        base_url: str, api_key: str, provider_name: str = "Custom",
        tools: list = None
    ):
        """
        Generic streaming untuk API yang kompatibel dengan OpenAI format.
        Sumopod, Together AI, Groq, dsb semua pakai format ini.
        """
        import re as _re

        def _is_html_content(text: str) -> bool:
            """Detect if a chunk is raw HTML (error page from provider like Sumopod/Cloudflare)."""
            stripped = text.lstrip()
            return (
                stripped.lower().startswith("<!doctype") or
                stripped.lower().startswith("<html") or
                "<body" in stripped.lower() or
                "service is not reachable" in stripped.lower() or
                "make sure the service is running" in stripped.lower()
            )

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            
            kwargs = {}
            if tools:
                kwargs["tools"] = tools

            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            html_buffer = ""
            is_buffering = True
            tool_calls_buffer = {}

            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                
                # Check for tool calls first
                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {"name": tc.function.name or "", "args": tc.function.arguments or ""}
                        else:
                            if tc.function.name:
                                tool_calls_buffer[idx]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_buffer[idx]["args"] += tc.function.arguments
                
                content_chunk = delta.content
                if not content_chunk:
                    continue

                # Safety: buffer early chunks to detect if provider returned an HTML error page
                if is_buffering:
                    html_buffer += content_chunk
                    if len(html_buffer) >= 64 or chunk.choices[0].finish_reason:
                        if _is_html_content(html_buffer):
                            log.warning(f"HTML error page detected from {provider_name}, suppressing")
                            yield f"\n❌ **Gagal menghubungi API ({provider_name}):** Layanan tidak dapat dijangkau (server mengembalikan halaman error). Coba lagi nanti atau ganti model."
                            return
                        else:
                            # Buffer is clean — flush it and switch to direct mode
                            yield html_buffer
                            is_buffering = False
                            html_buffer = None
                else:
                    # Past buffering phase — stream directly
                    yield content_chunk

            # Flush remaining buffer if stream ended before threshold
            if is_buffering and html_buffer:
                if not _is_html_content(html_buffer):
                    yield html_buffer
                else:
                    yield f"\n❌ **Gagal menghubungi API ({provider_name}):** Layanan tidak dapat dijangkau (server mengembalikan halaman error). Coba lagi nanti atau ganti model."

            for idx, tc in tool_calls_buffer.items():
                try:
                    import json
                    args_dict = json.loads(tc["args"])
                except:
                    args_dict = tc["args"]
                yield {"type": "tool_call", "name": tc["name"], "args": args_dict}

        except Exception as e:
            err_str = str(e)

            # Detect raw HTML error body embedded in exception (some httpx/openai versions do this)
            if _is_html_content(err_str) or "<!doctype" in err_str.lower() or "<html" in err_str.lower():
                yield f"\n❌ **Gagal menghubungi API ({provider_name}):** Layanan tidak dapat dijangkau (server down / halaman error). Coba lagi nanti atau ganti model."
                return

            # Handle empty/HTML response errors
            if "expecting value" in err_str.lower() or "char 0" in err_str.lower():
                yield f"\n❌ **Gagal menghubungi API ({provider_name}):** Provider mengembalikan respons kosong atau tidak valid (kemungkinan sedang maintenance atau limit tercapai)."
                return

            # "Request blocked" — content filter triggered
            # Auto-retry once with stripped/minimal system prompt before raising
            if "request was blocked" in err_str.lower() or "content filter" in err_str.lower() or "content_filter" in err_str.lower():
                log.warning(f"{provider_name}: request blocked by content filter, retrying with minimal prompt", error=err_str[:120])
                
                # Build simplified messages: strip heavy system prompt, keep user messages
                minimal_sys = (
                    "You are AI Orchestrator, a helpful AI assistant. "
                    "Respond naturally in Bahasa Indonesia. Be concise and professional."
                )
                retry_messages = [{"role": "system", "content": minimal_sys}]
                for m in messages:
                    if m["role"] != "system":
                        retry_messages.append(m)
                
                try:
                    retry_stream = await client.chat.completions.create(
                        model=model,
                        messages=retry_messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True,
                    )
                    async for rchunk in retry_stream:
                        rdelta = rchunk.choices[0].delta.content
                        if rdelta:
                            yield rdelta
                    log.info(f"{provider_name}: content filter retry succeeded")
                    return
                except Exception as retry_err:
                    log.error(f"{provider_name}: content filter retry also failed", error=str(retry_err)[:120])
                    raise RuntimeError(f"content filter blocked: {err_str}") from e

            # "Model output empty" — Sumopod-specific transient error, raise so executor can retry
            if ("model output must contain" in err_str.lower() or
                    "output text or tool calls" in err_str.lower() or
                    "cannot both be empty" in err_str.lower()):
                raise RuntimeError(f"model output error: {err_str}") from e
            elif "overdue balance" in err_str.lower() or "insufficient_quota" in err_str.lower():
                yield f"\n❌ API Key ({provider_name}) Anda kehabisan saldo. Silakan isi ulang saldo / ganti API Key di menu Integrations."
            elif "401" in err_str or "user not found" in err_str.lower() or "unauthorized" in err_str.lower() or "invalid_api_key" in err_str.lower():
                yield f"\n❌ API Key / Autentikasi ({provider_name}) tidak valid (401). Silakan periksa kembali API Key di menu Integrasi."
            elif "service is not reachable" in err_str.lower() or "502" in err_str or "503" in err_str:
                raise RuntimeError(f"Service unreachable ({provider_name}): {err_str}")
            else:
                clean_err = _re.sub(r"Error code: \d+ - ", "", err_str).strip()
                if "{'error'" in clean_err or '{"error"' in clean_err:
                    import ast
                    try:
                        err_dict = ast.literal_eval(clean_err)
                        if isinstance(err_dict, dict) and "error" in err_dict and "message" in err_dict["error"]:
                            clean_err = err_dict["error"]["message"]
                    except:
                        pass
                
                # Jika error mengandung kata kunci koneksi/timeout, raise agar executor bisa retry
                if any(k in clean_err.lower() for k in ["connection", "timeout", "network", "reachable"]):
                    raise RuntimeError(f"Connection error to {provider_name}: {clean_err}")
                
                yield f"\n❌ **Gagal menghubungi API ({provider_name}):** {clean_err}"

    # ── Ollama ────────────────────────────────────────────────
    async def _stream_ollama(self, model, messages, temperature, max_tokens, tools=None):
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            if tools:
                payload["tools"] = tools

            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{settings.OLLAMA_HOST}/api/chat",
                    json=payload,
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line:
                            data = json.loads(line)
                            msg = data.get("message", {})
                            content = msg.get("content", "")
                            if content:
                                yield content
                            
                            if "tool_calls" in msg and msg["tool_calls"]:
                                for tc in msg["tool_calls"]:
                                    yield {
                                        "type": "tool_call",
                                        "name": tc["function"]["name"],
                                        "args": tc["function"]["arguments"]
                                    }
        except Exception as e:
            yield f"\n[Error Ollama: {e}. Pastikan Ollama berjalan: ollama serve]"

    # ── Vision: gambar → teks ────────────────────────────────
    async def chat_with_image(
        self,
        image_b64: str,
        mime_type: str,
        text_prompt: str,
        system_prompt: str = "",
        history: list = None,
        model: str = None,
    ) -> str:
        """
        Kirim gambar (base64) + teks ke vision-capable model.
        Auto-fallback: OpenAI gpt-5-mini → Sumopod (OpenAI-compatible) → Google Gemini.
        """
        history = history or []
        model_to_use = model

        # Auto-detect vision model jika tidak ditentukan
        if not model_to_use:
            vision_candidates = [
                m for m in self.available_models
                if any(v in m for v in ["gemini-2.5-flash", "qwen3.6-plus", "vision"])
            ]
            if vision_candidates:
                model_to_use = vision_candidates[0]
            else:
                model_to_use = self.get_default_model()

        provider = self._get_provider(model_to_use)
        clean_model = model_to_use.replace("sumopod/", "").replace("ollama/", "")
        image_url = f"data:{mime_type};base64,{image_b64}"

        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        for h in (history or [])[-6:]:
            msgs.append(h)
        msgs.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": text_prompt},
            ],
        })

        try:
            if provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                resp = await client.chat.completions.create(
                    model=clean_model, messages=msgs, max_tokens=2048, temperature=0.5,
                )
                return resp.choices[0].message.content or ""

            elif provider in ("sumopod", "custom"):
                if provider == "sumopod":
                    base_url = settings.SUMOPOD_HOST
                    api_key  = settings.SUMOPOD_API_KEY
                    actual_model = clean_model
                else:
                    info = self.available_models.get(model_to_use, {})
                    base_url = info.get("base_url", "")
                    api_key  = info.get("api_key", "")
                    actual_model = info.get("model_id", clean_model)
                if base_url and api_key:
                    from openai import AsyncOpenAI
                    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                    resp = await client.chat.completions.create(
                        model=actual_model, messages=msgs, max_tokens=2048, temperature=0.5,
                    )
                    return resp.choices[0].message.content or ""

            elif provider == "google":
                import asyncio
                import google.generativeai as genai
                import base64 as _b64, io
                import PIL.Image
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                gmodel = genai.GenerativeModel(clean_model)
                pil_img = PIL.Image.open(io.BytesIO(_b64.b64decode(image_b64)))
                
                # Jalankan sinkronous API Gemini di thread pool agar tidak memblokir event loop
                loop = asyncio.get_event_loop()
                def _generate_sync():
                    return gmodel.generate_content([pil_img, text_prompt])
                    
                resp = await loop.run_in_executor(None, _generate_sync)
                try:
                    return resp.text or ""
                except ValueError:
                    # Ini terjadi jika terblokir oleh safety filter Gemini
                    return "❌ Respons diblokir oleh filter keamanan Google Gemini (Safety Block)."

        except Exception as e:
            log.error("chat_with_image error", model=model_to_use, error=str(e))
            return f"❌ Gagal memproses gambar via {model_to_use}: {e}"

        return "❌ Tidak ada model vision yang tersedia. Tambahkan model yang mendukung gambar (gemini/gemini-2.5-flash, qwen3.6-plus) di menu Integrasi."

    # ── Image Generation: teks → gambar ───────────────────────
    async def generate_image(
        self,
        prompt: str,
        model: str = None,
        size: str = "1024x1024",
        n: int = 1,
    ) -> Optional[str]:
        """
        Generate image from text prompt using /images/generations endpoint.
        Returns URL of generated image or None if not supported.

        Tries providers in order: OpenAI → Sumopod → Custom endpoints.
        """
        # 1. Try OpenAI DALL-E
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-..."):
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                image_model = model if model and "dall" in model.lower() else "dall-e-3"
                if image_model not in (self.available_models or {}):
                    image_model = "dall-e-3"  # default DALL-E model
                resp = await client.images.generate(
                    model=image_model,
                    prompt=prompt,
                    n=n,
                    size=size,
                )
                if resp.data and resp.data[0].url:
                    log.info("generate_image: OpenAI success", model=image_model)
                    return resp.data[0].url
            except Exception as e:
                err = str(e)
                if "model_not_found" in err or "invalid_model" in err:
                    pass  # model not available, try next provider
                else:
                    log.debug("generate_image: OpenAI failed", error=err[:80])

        # 2. Try Sumopod (OpenAI-compatible)
        if settings.SUMOPOD_API_KEY:
            try:
                import httpx
                headers = {
                    "Authorization": f"Bearer {settings.SUMOPOD_API_KEY}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model or "mimo-v2-omni",
                    "prompt": prompt,
                    "n": n,
                    "size": size,
                    "response_format": "url",
                }
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        f"{settings.SUMOPOD_HOST}/images/generations",
                        json=payload,
                        headers=headers,
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("data") and data["data"][0].get("url"):
                        log.info("generate_image: Sumopod success", model=model)
                        return data["data"][0]["url"]
                    elif data.get("data") and data["data"][0].get("b64_json"):
                        # Return as data URI if base64
                        b64 = data["data"][0]["b64_json"]
                        return f"data:image/png;base64,{b64}"
                else:
                    log.debug("generate_image: Sumopod returned", status=resp.status_code)
            except Exception as e:
                log.debug("generate_image: Sumopod failed", error=str(e)[:80])

        # 3. Try custom model providers
        from db.database import AsyncSessionLocal
        from db.models import CustomModel
        from sqlmodel import select
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(CustomModel).where(CustomModel.is_active == True)
                )
                custom_models = result.scalars().all()

            for cm in custom_models:
                if not cm.api_key or not cm.base_url:
                    continue
                try:
                    import httpx
                    payload = {
                        "model": cm.model_id,
                        "prompt": prompt,
                        "n": n,
                        "size": size,
                    }
                    headers = {
                        "Authorization": f"Bearer {cm.api_key}",
                        "Content-Type": "application/json",
                    }
                    async with httpx.AsyncClient(timeout=60) as client:
                        resp = await client.post(
                            f"{cm.base_url.rstrip('/')}/images/generations",
                            json=payload,
                            headers=headers,
                        )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("data") and data["data"][0].get("url"):
                            log.info("generate_image: custom model success", model=cm.model_id)
                            return data["data"][0]["url"]
                except Exception:
                    continue
        except Exception:
            pass

        log.info("generate_image: no provider succeeded, returning None")
        return None


    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str = "audio.ogg",
    ) -> str:
        """
        Transkrip audio ke teks menggunakan Whisper API.
        Auto-fallback: OpenAI Whisper → Sumopod Whisper-compatible.
        """
        import io

        # 1. Coba OpenAI Whisper
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-..."):
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = filename
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                    language="id",
                )
                return str(transcript)
            except Exception as e:
                log.warning("OpenAI Whisper failed, trying Sumopod", error=str(e)[:80])

        # Cari model audio/tts yang tersedia
        from core.capability_map import capability_map
        best_audio_model = capability_map.find_best_model({"audio"})
        sumopod_model = best_audio_model if best_audio_model else "whisper-1"

        # 2. Coba Sumopod (jika mendukung whisper-compatible endpoint)
        if settings.SUMOPOD_API_KEY:
            try:
                from openai import AsyncOpenAI
                audio_file2 = io.BytesIO(audio_bytes)
                audio_file2.name = filename
                client = AsyncOpenAI(
                    api_key=settings.SUMOPOD_API_KEY,
                    base_url=settings.SUMOPOD_HOST,
                )
                transcript = await client.audio.transcriptions.create(
                    model=sumopod_model,
                    file=audio_file2,
                    response_format="text",
                )
                return str(transcript)
            except Exception as e:
                log.warning("Sumopod Whisper failed", model=sumopod_model, error=str(e)[:80])

        return ""

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

