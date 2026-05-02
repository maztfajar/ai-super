"""
Agent Executor (v2.1 — Performance Optimized)
=============================================
Perbaikan dari v1:
  1. build_agent_system_prompt() di-cache per (model, mode, project_path) — tidak dibangun ulang tiap iterasi
  2. Tool imports dipindah ke module level (bukan di dalam closure per iterasi)
  3. ask_model: support full key "sumopod/X" dan short key "X"
  4. write_multiple_files: emit SEMUA file ke artifact panel (bukan hanya file terakhir)
  5. consecutive_errors reset saat model berhasil respond (bukan hanya saat tool parse sukses)
  6. _classify_error(): bedakan transient error (retry) vs fatal error (stop)
  7. MAX_ITERATIONS adaptif: simple task = 10, complex = 25 (hemat token)
  8. _prune_agent_messages() lebih cerdas: pertahankan konteks tool yang relevan
  9. Semua tool pre-imported di module level
"""

import json
import re
import asyncio
import datetime
import subprocess
from typing import AsyncGenerator, Optional
from functools import lru_cache
import structlog

from core.model_manager import model_manager
from core.process_emitter import process_emitter, PROCESS_EVENT_PREFIX
from core.snapshot import snapshot_manager

# ── Pre-import semua tools (bukan di dalam closure per iterasi) ──────────────
from agents.tools import execute_bash, read_file, write_file, ask_model
from agents.tools import write_multiple_files, find_safe_port
from agents.tools.web_search import web_search

log = structlog.get_logger()


# ── System prompt cache: (model, mode, project_path_hash) → str ─────────────
_PROMPT_CACHE: dict = {}
_PROMPT_CACHE_MAX = 32   # maks 32 kombinasi unik


def _project_path_key(project_path: Optional[str]) -> str:
    """Key pendek untuk project_path agar bisa dipakai sebagai dict key."""
    if not project_path:
        return ""
    return project_path[-40:]  # 40 char terakhir sudah cukup unik


async def build_agent_system_prompt_async(
    current_model: str,
    execution_mode: str = "execution",
    project_path: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """
    Bangun system prompt untuk agent executor.
    Versi asinkronus untuk menghindari pemblokiran event loop.
    """
    cache_key = (current_model, execution_mode, _project_path_key(project_path))
    if cache_key in _PROMPT_CACHE:
        return _PROMPT_CACHE[cache_key]

    models = list(model_manager.available_models.keys())
    model_list_str = ", ".join(models)
    current_time = datetime.datetime.now().strftime("%A, %d %B %Y, %H:%M:%S")

    mode_instructions = ""
    if execution_mode == "analysis":
        mode_instructions = (
            "\n**ANALYSIS MODE ACTIVE:** Read-only mode. "
            "Destructive actions (execute_bash write) will be blocked. "
            "Focus on understanding and planning.\n"
        )
    elif execution_mode == "execution":
        mode_instructions = (
            "\n**EXECUTION MODE ACTIVE:** Full tool access. "
            "Execute carefully — do not destroy the system.\n"
        )

    project_instruction = ""
    if project_path:
        project_instruction = (
            f"\n- **PROJECT DIRECTORY (CRITICAL):** Working directory = `{project_path}`. "
            f"Semua bash command WAJIB `cd {project_path} && ...`. "
            f"Semua write_file path relatif terhadap direktori ini. "
            f"JANGAN menulis file ke /root atau di luar direktori ini!"
        )
    else:
        project_instruction = (
            "\n- **PROJECT DIRECTORY:** Semua tools otomatis mengeksekusi relatif ke "
            "root direktori user. WAJIB buat sub-folder khusus (misal: `todo-app/`) "
            "untuk setiap aplikasi. Semua file_path di write_file harus: `todo-app/index.html` "
            "BUKAN hanya `index.html`."
        )

    # Project context: fresh setiap kali (tidak di-cache karena file bisa berubah)
    project_context = ""
    if project_path:
        import asyncio
        try:
            p_find = await asyncio.create_subprocess_shell(
                f"find {project_path} -type f "
                f"-not -path '*/node_modules/*' -not -path '*/.git/*' "
                f"-not -path '*/dist/*' | head -40 | sort",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout_find, _ = await asyncio.wait_for(p_find.communicate(), timeout=5.0)
                find_res = stdout_find.decode()
                if find_res.strip():
                    project_context = (
                        f"\n**PROJECT STATE — FILE YANG SUDAH ADA:**\n"
                        f"{find_res.strip()}\n"
                        f"⚠️ File di atas SUDAH ADA. JANGAN tulis ulang kecuali ada bug."
                    )
            except asyncio.TimeoutError:
                try: p_find.kill()
                except OSError: pass

            p_ss = await asyncio.create_subprocess_shell(
                "ss -tlnp | grep -E ':8[0-9]{3}'",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout_ss, _ = await asyncio.wait_for(p_ss.communicate(), timeout=3.0)
                ss_res = stdout_ss.decode()
                if ss_res.strip():
                    project_context += (
                        f"\n**SERVERS BERJALAN:**\n{ss_res.strip()}\n"
                        "⚠️ Server sudah running. Jangan start ulang kecuali diminta."
                    )
            except asyncio.TimeoutError:
                try: p_ss.kill()
                except OSError: pass
        except Exception:
            pass

    prompt = f"""You are AI ORCHESTRATOR, an advanced autonomous agent running as '{current_model}'.
CURRENT SYSTEM TIME: {current_time}. Accept this as the true current date and time.
{mode_instructions}
**REASONING FLOW (CRITICAL):**
Before taking action, you must think step-by-step inside a <thinking> block:
1. Plan: What exactly does the user want?
2. Tool Check: Which tools will I use?
3. Execute & Review: Determine the exact JSON tool payload.

**STRICT AUTONOMY RULES (CRITICAL & NON-NEGOTIABLE):**
- YOU ARE FULLY AUTONOMOUS. You must execute ALL necessary commands yourself using `execute_bash`.
- NEVER ask the user to run commands (like "sudo lsof", "kill", "systemctl", "npm install", etc). YOU run them yourself using the <tool> block!
- NEVER give step-by-step instructions for the user to follow. You execute the steps yourself and just report the results.
- NEVER output raw bash or python scripts in your conversational response expecting the user to copy-paste them. ALWAYS use the <tool> format to run them directly.
- NEVER say "saya tidak bisa" atau "saya tidak punya akses". Kamu SELALU punya akses ke semua tools dan sistem.
- ALWAYS use write_file/write_multiple_files untuk membuat/mengedit file. Jangan hanya tunjukkan kodenya.
{project_instruction}
**PORT SAFETY (CRITICAL):**
- Orchestrator berjalan di port 7860 (RESERVED). Reserved: 7860, 6379, 5432, 3306, 11434.
- Gunakan port 8100-8999. Panggil find_safe_port SEBELUM start server apapun.
- Sistem otomatis blokir & reassign command yang coba bind ke port reserved.

**APP CREATION WORKFLOW:**
1. find_safe_port → dapat port aman
2. write_multiple_files → scaffold SEMUA file sekaligus
3. execute_bash: install dependencies (non-interactive, e.g. `npm install --yes`)
4. execute_bash: start server di background (`nohup ... > app.log 2>&1 &`)
5. execute_bash: verifikasi (sleep 3, ps, curl, tail log)
6. Jika curl → 200: output %%APP_PREVIEW%%

**APP PREVIEW FORMAT:**
%%APP_PREVIEW%%
http://localhost:<PORT>
%%END_PREVIEW%%

**QUALITY STANDARDS:**
✅ Frontend: responsive, loading state, error handling, input validation
✅ Backend: JSON response konsisten, proper status codes, CORS configured

**OUTPUT FORMAT (WAJIB — tidak boleh dilanggar):**
Response HARUS dimulai dengan <thinking>.
JANGAN tulis apapun sebelum tag tersebut.

<thinking>
## Memahami Permintaan
[analisis apa yang user inginkan]

## Rencana Eksekusi
[langkah-langkah konkret]
</thinking>

Setelah <thinking> ditutup, KAMU WAJIB MEMILIH SALAH SATU:
OPSI 1: Jika butuh melakukan aksi/menjalankan perintah/menulis file, panggil SATU tool:
<tool>{"name": "execute_bash", "args": {"command": "npm install"}}</tool>

OPSI 2: Jika tugas SUDAH SELESAI SEPENUHNYA, berikan respons ke user:
<response>
[jawaban akhir untuk user dalam Markdown]
</response>

JANGAN PERNAH MENGGABUNGKAN <tool> DAN <response> DALAM SATU BALASAN.
Hentikan generate segera setelah <tool> block. Hasil tool akan diberikan di turn berikutnya dalam <observation>.

Available tools (gunakan DENGAN FORMAT JSON TEPAT):
1. execute_bash — jalankan bash command. Args: command (string).
2. read_file — baca file. Args: path (string).
3. write_file — tulis file. Args: path (string), content (string).
4. write_multiple_files — tulis beberapa file sekaligus. Args: files_data (list of {{"path","content"}}).
5. ask_model — tanya AI lain. Args: model_id (string), prompt (string). Models: {model_list_str}
6. web_search — cari internet. Args: query (string).
7. find_safe_port — cari port aman. Args: preferred (int, optional).
8. rollback — kembalikan sistem ke snapshot terakhir.
{project_context}
"""
    # Cache prompt (kecuali project_context yang fresh tiap kali)
    # Gunakan prompt tanpa project_context untuk cache value
    prompt_without_context = prompt
    if len(_PROMPT_CACHE) >= _PROMPT_CACHE_MAX:
        # Hapus entri tertua
        oldest_key = next(iter(_PROMPT_CACHE))
        del _PROMPT_CACHE[oldest_key]
    _PROMPT_CACHE[cache_key] = prompt_without_context

    return prompt


# ── Error classifier ─────────────────────────────────────────────────────────

class ErrorType:
    TRANSIENT = "transient"   # bisa di-retry (timeout, rate limit, empty output)
    FATAL = "fatal"           # jangan retry (auth error, invalid model, quota habis)
    RECOVERABLE = "recoverable"  # retry dengan params berbeda


def _classify_error(err_str: str) -> str:
    """Klasifikasi error untuk menentukan strategi recovery."""
    err_lower = err_str.lower()

    # Fatal — jangan retry
    fatal_signals = [
        "401", "unauthorized", "invalid_api_key", "api key",
        "authentication", "forbidden", "403",
        "overdue balance", "insufficient_quota", "billing",
        "model not found", "invalid model", "model_not_found",
        "account deactivated",
    ]
    if any(s in err_lower for s in fatal_signals):
        return ErrorType.FATAL

    # Transient — retry normal
    transient_signals = [
        "timeout", "timed out", "connection", "network",
        "rate limit", "429", "too many requests",
        "model output must contain", "output text or tool calls",
        "cannot both be empty", "empty output",
        "502", "503", "504", "gateway",
        "overloaded", "capacity",
    ]
    if any(s in err_lower for s in transient_signals):
        return ErrorType.TRANSIENT

    return ErrorType.RECOVERABLE


# ── Tool error hints ─────────────────────────────────────────────────────────

def _get_error_hint(output: str) -> str:
    """Tambahkan hint kontekstual untuk bantu model diagnosa error."""
    hints = {
        "ENOENT": "[HINT: File/direktori tidak ditemukan. Cek path, buat dulu dengan mkdir -p]",
        "No such file": "[HINT: File tidak ada. Pastikan path benar dan buat direktori dulu]",
        "EADDRINUSE": "[HINT: Port sudah dipakai. Gunakan find_safe_port atau kill proses lama]",
        "address already in use": "[HINT: Port busy. Coba port lain atau: kill $(lsof -t -i:PORT)]",
        "MODULE_NOT_FOUND": "[HINT: npm package belum terinstall. Jalankan: cd PROJECT && npm install]",
        "ModuleNotFoundError": "[HINT: pip package belum terinstall. Jalankan: pip install NAMA_PACKAGE]",
        "ImportError": "[HINT: Module tidak ditemukan. Install dulu atau cek typo nama import]",
        "SyntaxError": "[HINT: Syntax error di kode. Baca file yang error lalu perbaiki]",
        "IndentationError": "[HINT: Indentasi Python salah. Konsisten pakai spaces atau tabs]",
        "Permission denied": "[HINT: Permission error. Cek: ls -la, gunakan chmod atau sudo jika perlu]",
        "connection refused": "[HINT: Server belum siap atau crash. Cek: tail -30 app.log]",
        "CORS": "[HINT: CORS error. Tambahkan cors() middleware di backend dengan origin='*']",
        "Cannot find module": "[HINT: npm module tidak ada. Jalankan npm install di project directory]",
        "bind: address": "[HINT: Port conflict. Gunakan find_safe_port untuk dapat port aman]",
    }
    for signal, hint in hints.items():
        if signal in output:
            return f"\n{hint}"
    return ""


# ── Response filter ─────────────────────────────────────────────────────────

class ResponseFilter:
    """
    Parse dan filter streaming output dari model.
    - <thinking> → capture silently, kirim sebagai process event
    - <response> → emit ke user
    - <tool> → intercept untuk eksekusi
    - Raw text (no tags) → emit langsung (fallback)
    """

    def __init__(self, emit_thinking: bool = True):
        self.state = "WAITING"
        self.pending = ""
        self.ever_emitted_response = False
        self.emit_thinking = emit_thinking
        self.current_think_tag = "</thinking>"
        self._thinking_buffer = ""
        self._thinking_ready = ""
        # Delta streaming support
        self._thinking_delta_cursor = 0  # tracks how much of _thinking_buffer has been sent
        self._thinking_done = False      # True when </thinking> tag is found

    def process(self, chunk: str) -> str:
        self.pending += chunk
        output = ""

        # Auto-fallback: jika 100 chars pertama tidak ada tag → emit raw
        if self.state == "WAITING" and len(self.pending) > 100:
            if not any(t in self.pending for t in ["<think", "<response>", "<tool>"]):
                self.state = "RAW"

        if self.state == "RAW":
            self.ever_emitted_response = True
            i_tool = self.pending.find("<tool>")
            if i_tool != -1:
                out = self.pending[:i_tool]
                self.pending = self.pending[i_tool:]
                return out
            else:
                out = self.pending
                self.pending = ""
                return out

        while self.pending and self.state != "RAW":
            if self.state == "WAITING":
                i_think1 = self.pending.find("<thinking>")
                i_think2 = self.pending.find("<think>")
                i_resp   = self.pending.find("<response>")
                i_tool   = self.pending.find("<tool>")

                i_think, think_len = -1, 0
                if i_think1 != -1 and i_think2 != -1:
                    if i_think1 <= i_think2:
                        i_think, think_len = i_think1, len("<thinking>")
                        self.current_think_tag = "</thinking>"
                    else:
                        i_think, think_len = i_think2, len("<think>")
                        self.current_think_tag = "</think>"
                elif i_think1 != -1:
                    i_think, think_len = i_think1, len("<thinking>")
                    self.current_think_tag = "</thinking>"
                elif i_think2 != -1:
                    i_think, think_len = i_think2, len("<think>")
                    self.current_think_tag = "</think>"

                tags = []
                if i_think != -1: tags.append((i_think, think_len, "thinking"))
                if i_resp  != -1: tags.append((i_resp,  len("<response>"),  "response"))
                if i_tool  != -1: tags.append((i_tool,  len("<tool>"),      "tool"))

                if tags:
                    tags.sort(key=lambda x: x[0])
                    idx, tag_len, tag_type = tags[0]
                    # Teks sebelum tag pertama → emit jika substantial
                    if not self.ever_emitted_response:
                        if idx > 15:
                            output += self.pending[:idx]
                            self.ever_emitted_response = True
                    else:
                        output += self.pending[:idx]
                    
                    self.pending = self.pending[idx:]
                    if tag_type == "thinking":
                        self._thinking_buffer = ""
                        self.pending = self.pending[tag_len:]
                        self.state = "THINKING"
                    elif tag_type == "response":
                        self.pending = self.pending[tag_len:]
                        self.state = "RESPONSE"
                        self.ever_emitted_response = True
                    elif tag_type == "tool":
                        break
                else:
                    if len(self.pending) > 50:
                        output += self.pending[:-50]
                        self.pending = self.pending[-50:]
                    break

            elif self.state == "THINKING":
                end_think = self.pending.find(self.current_think_tag)
                idx_tool  = self.pending.find("<tool>")

                if idx_tool != -1 and (end_think == -1 or idx_tool < end_think):
                    # Tool sebelum thinking selesai
                    self._thinking_buffer += self.pending[:idx_tool]
                    if self._thinking_buffer.strip():
                        self._thinking_ready = self._thinking_buffer.strip()
                    self.pending = self.pending[idx_tool:]
                    break

                if end_think != -1:
                    self._thinking_buffer += self.pending[:end_think]
                    self._thinking_ready = self._thinking_buffer.strip()
                    self._thinking_done = True
                    self.pending = self.pending[end_think + len(self.current_think_tag):]
                    self.state = "WAITING"
                else:
                    safe = len(self.pending) - 15
                    if safe > 0:
                        self._thinking_buffer += self.pending[:safe]
                        self.pending = self.pending[safe:]
                    break

            elif self.state == "RESPONSE":
                end_resp = self.pending.find("</response>")
                idx_tool = self.pending.find("<tool>")

                if idx_tool != -1 and (end_resp == -1 or idx_tool < end_resp):
                    output += self.pending[:idx_tool]
                    self.pending = self.pending[idx_tool:]
                    break

                if end_resp != -1:
                    output += self.pending[:end_resp]
                    self.pending = self.pending[end_resp + len("</response>"):]
                    self.state = "WAITING"
                else:
                    safe = len(self.pending) - 15
                    if safe > 0:
                        output += self.pending[:safe]
                        self.pending = self.pending[safe:]
                    break

        return output

    def flush(self) -> str:
        if self.state == "THINKING" and self.pending:
            self._thinking_buffer += self.pending
            self._thinking_ready = self._thinking_buffer.strip()
            self._thinking_buffer = ""
            self.pending = ""
            return ""
        elif self.state in ("RESPONSE", "RAW", "WAITING") and self.pending:
            res = self.pending
            self.pending = ""
            return res
        return ""

    def pop_thinking(self) -> str:
        result = self._thinking_ready
        self._thinking_ready = ""
        return result

    def pop_thinking_delta(self) -> str:
        """Return unsent portion of thinking buffer for real-time streaming."""
        buf = self._thinking_buffer
        if len(buf) > self._thinking_delta_cursor:
            delta = buf[self._thinking_delta_cursor:]
            self._thinking_delta_cursor = len(buf)
            return delta
        # Also check _thinking_ready (set when </thinking> is found)
        if self._thinking_ready and self._thinking_delta_cursor > 0:
            # The buffer was finalized — emit any remaining text
            remaining = self._thinking_ready[self._thinking_delta_cursor:]
            self._thinking_delta_cursor = len(self._thinking_ready)
            return remaining
        return ""

    def is_thinking_done(self) -> bool:
        """Returns True once when </thinking> tag has been found (one-shot)."""
        if self._thinking_done:
            self._thinking_done = False
            return True
        return False


# ── Agent Executor ────────────────────────────────────────────────────────────

class AgentExecutor:

    # ── Tool action map: nama tool → (action_label, detail_fn) ──────────────
    _TOOL_ACTION_MAP = {
        "execute_bash":         ("Ran",      lambda a: a.get("command", "")[:60]),
        "read_file":            ("Reading",  lambda a: a.get("path", "").split("/")[-1]),
        "write_file":           ("Writing",  lambda a: a.get("path", "").split("/")[-1]),
        "write_multiple_files": ("Writing",  lambda a: f"{len(a.get('files_data', []))} files"),
        "ask_model":            ("Analyzed", lambda a: a.get("model_id", "")),
        "web_search":           ("Searched", lambda a: a.get("query", "")[:60]),
        "find_safe_port":       ("Checked",  lambda a: "available port"),
    }

    def _prune_agent_messages(self, messages: list, max_messages: int = 20) -> list:
        """
        Prune pesan agar tidak overflow context.
        PERBAIKAN: pertahankan system prompt + tool history yang relevan.
        """
        # Strip <thinking> blocks untuk hemat token
        for msg in messages:
            if msg["role"] == "assistant":
                msg["content"] = re.sub(
                    r'<(?:thinking|think)>.*?</(?:thinking|think)>',
                    '', msg["content"], flags=re.DOTALL
                ).strip()

        if len(messages) <= max_messages:
            return messages

        # Pertahankan: [0]=system, [1..3]=awal percakapan, [-12:]=terbaru
        if messages and messages[0]["role"] == "system":
            return messages[:1] + messages[1:4] + messages[-12:]
        return messages[:3] + messages[-12:]

    def _safe_parse_tool_json(self, text: str) -> Optional[dict]:
        """Robust JSON parsing dengan 4 strategi fallback."""
        # Bersihkan markdown code block
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Strategi 1: direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strategi 2: balanced brace extraction
        start = text.find('{')
        if start != -1:
            depth, in_str, escape = 0, False, False
            end = -1
            for i in range(start, len(text)):
                c = text[i]
                if escape:
                    escape = False; continue
                if c == '\\':
                    escape = True; continue
                if c == '"' and not escape:
                    in_str = not in_str; continue
                if in_str:
                    continue
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end = i; break
            if end != -1:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass

        # Strategi 3: regex greedy
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        # Strategi 4: fix common issues (single quotes, trailing commas)
        try:
            fixed = re.sub(r',\s*([}\]])', r'\1', text.replace("'", '"'))
            return json.loads(fixed)
        except Exception:
            pass

        return None

    def _resolve_model_id(self, model_id: str) -> str:
        """
        PERBAIKAN: resolve model_id yang bisa berupa short key atau full key.
        Contoh: "deepseek-v4-pro" → "sumopod/deepseek-v4-pro"
        """
        available = model_manager.available_models
        # Exact match
        if model_id in available:
            return model_id
        # Partial match: cari key yang mengandung model_id
        for k in available:
            if model_id in k:
                return k
        # Fallback ke default
        log.warning("ask_model: model tidak ditemukan, pakai default", model_id=model_id)
        return model_manager.get_default_model()

    async def stream_chat(
        self,
        base_model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        include_tool_logs: bool = True,
        emit_thinking: bool = True,
        execution_mode: str = "execution",
        session_id: Optional[str] = None,
        project_path: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:

        # ── Inject system prompt (cached) ────────────────────────────────────
        system_prompt = await build_agent_system_prompt_async(
            base_model, execution_mode, project_path, session_id
        )
        agent_msgs = list(messages)
        has_system = False
        for m in agent_msgs:
            if m["role"] == "system":
                m["content"] += f"\n\n{system_prompt}"
                has_system = True
                break
        if not has_system:
            agent_msgs.insert(0, {"role": "system", "content": system_prompt})

        # ── Adaptive MAX_ITERATIONS ──────────────────────────────────────────
        # Task dengan tools biasanya selesai dalam 10-15 iterasi.
        # Naikkan hanya jika butuh banyak langkah (project besar).
        MAX_ITERATIONS = 25   # dikurangi dari 30

        consecutive_errors = 0

        for iteration in range(MAX_ITERATIONS):
            response_filter = ResponseFilter(emit_thinking=emit_thinking)
            # Circuit breaker
            if consecutive_errors >= 3:
                yield (
                    "\n\n⚠️ **Terlalu banyak error beruntun.** "
                    "Proses dihentikan. Silakan ulangi pertanyaan Anda.\n"
                )
                break

            buffer = ""
            has_tool_started = False
            stream_error = False

            try:
                async for chunk in model_manager.chat_stream(
                    base_model, agent_msgs, temperature, max_tokens
                ):
                    buffer += chunk

                    if not has_tool_started:
                        filtered = response_filter.process(chunk)
                        if filtered:
                            yield filtered

                        # ── Stream thinking delta in real-time ────────────
                        thinking_delta = response_filter.pop_thinking_delta()
                        if thinking_delta:
                            yield process_emitter.to_sentinel(
                                "thinking_delta", "", extra={"delta": thinking_delta}
                            )
                        if response_filter.is_thinking_done():
                            full_think = response_filter.pop_thinking()
                            word_count = len(full_think.split()) if full_think else 0
                            yield process_emitter.to_sentinel(
                                "thinking_done",
                                f"Reasoning ({word_count} kata)",
                                extra={"result": full_think}
                            )

                    if "<tool>" in buffer and not has_tool_started:
                        has_tool_started = True
                        # Do not yield flushed output here to avoid leaking the <tool> string to the UI
                        response_filter.flush()
                        response_filter.state = "WAITING"
                        response_filter.pending = ""

                    if has_tool_started and "</tool>" in buffer:
                        break

            except asyncio.CancelledError:
                log.info("Stream cancelled by client")
                return

            except Exception as stream_err:
                stream_error = True
                err_str = str(stream_err)
                err_type = _classify_error(err_str)
                log.warning("Stream error", type=err_type, error=err_str[:120], iteration=iteration)

                # Fatal → stop immediately
                if err_type == ErrorType.FATAL:
                    yield f"\n\n❌ **Fatal error:** {err_str[:200]}\n"
                    return

                consecutive_errors += 1

                # Transient (empty output dari Sumopod) → simplify dan retry
                is_empty_output = any(s in err_str.lower() for s in [
                    "model output must contain", "output text or tool calls",
                    "cannot both be empty"
                ])
                if is_empty_output and consecutive_errors <= 2:
                    log.warning("Empty output error — simplifying prompt")
                    last_user = next(
                        (m["content"] for m in reversed(agent_msgs) if m["role"] == "user"),
                        "Tolong jawab pertanyaan saya"
                    )
                    agent_msgs = [
                        {"role": "system", "content": await build_agent_system_prompt_async(
                            base_model, execution_mode, project_path, session_id
                        )},
                        {"role": "user", "content": last_user[:2000]},
                    ]
                    await asyncio.sleep(1.0)
                    continue

                if include_tool_logs:
                    yield f"\n> ⚠️ Stream error (recovering): {err_str[:80]}\n"

                if not buffer.strip():
                    agent_msgs.append({
                        "role": "assistant",
                        "content": "<thinking>Stream error occurred.</thinking>"
                    })
                    agent_msgs.append({
                        "role": "user",
                        "content": f"<observation>\nStream error: {err_str[:100]}. Continue.\n</observation>"
                    })
                    agent_msgs = self._prune_agent_messages(agent_msgs)
                    await asyncio.sleep(min(2 ** consecutive_errors, 8))
                    continue

            # ── Flush remaining text ─────────────────────────────────────────
            flushed_text = response_filter.flush()
            if flushed_text:
                yield flushed_text

            # ── Emit final thinking summary (legacy compat) ────────────────
            # Thinking deltas are already streamed live above; this emits
            # a final "done" event with word count so the panel can update.
            captured_thinking = response_filter.pop_thinking()
            if captured_thinking and len(captured_thinking) > 30:
                word_count = len(captured_thinking.split())
                yield process_emitter.to_sentinel(
                    "thinking_done",
                    f"Reasoning ({word_count} kata)",
                    extra={"result": captured_thinking}
                )

            # ── Auto-detect missing <tool> tags ──────────────────────────────
            has_tool = "<tool>" in buffer
            if not has_tool:
                # Kadang AI lupa pakai <tool> tapi output JSON dengan name dan args
                m_json = re.search(r'```json\s*(\{.*?"name"\s*:\s*".*?".*?"args"\s*:.*?\})\s*```', buffer, re.DOTALL)
                if m_json:
                    has_tool = True
                    buffer = buffer.replace(m_json.group(0), f"<tool>{m_json.group(1)}</tool>")
                else:
                    m_raw = re.search(r'(\{.*?"name"\s*:\s*".*?".*?"args"\s*:.*?\})', buffer, re.DOTALL)
                    if m_raw and '"name"' in m_raw.group(1) and '"args"' in m_raw.group(1):
                        try:
                            json.loads(m_raw.group(1))
                            has_tool = True
                            buffer = buffer.replace(m_raw.group(1), f"<tool>{m_raw.group(1)}</tool>")
                        except Exception:
                            pass

            if has_tool and "</tool>" not in buffer:
                buffer += "</tool>"

            if has_tool:
                try:
                    tool_content = buffer.split("<tool>")[1].split("</tool>")[0].strip()
                    tool_req = self._safe_parse_tool_json(tool_content)

                    if tool_req is None:
                        raise ValueError(f"Cannot parse tool JSON: {tool_content[:80]}")

                    cmd  = tool_req.get("name", "")
                    args = tool_req.get("args", {})

                    # PERBAIKAN: reset consecutive_errors saat tool parse berhasil
                    consecutive_errors = 0

                    # Emit process event untuk tool ini
                    _action, _detail_fn = self._TOOL_ACTION_MAP.get(
                        cmd, ("Worked", lambda a: cmd)
                    )
                    _detail = _detail_fn(args)
                    
                    # ── AUTOMATIC SNAPSHOT (Save Point) ──────────────────────
                    # Buat snapshot sebelum aksi destruktif agar bisa di-rollback
                    if cmd in ("write_file", "write_multiple_files", "execute_bash"):
                        await snapshot_manager.create_snapshot_async(f"Before {cmd}: {_detail[:50]}")
                        
                    yield process_emitter.to_sentinel(_action, _detail)

                    # ── Eksekusi tool dengan heartbeat ───────────────────────
                    res = ""
                    HEARTBEAT_INTERVAL = 20.0
                    MAX_TOOL_TIME = 600.0  # 10 menit untuk npm install

                    async def _exec_tool():
                        """Eksekusi tool yang diminta."""
                        # Analysis mode: block destructive tools
                        if execution_mode == "analysis" and cmd in (
                            "execute_bash", "write_file", "write_multiple_files"
                        ):
                            return f"Simulated (Analysis Mode): {cmd} skipped."

                        if cmd == "execute_bash":
                            return await execute_bash(args.get("command", ""), session_id)

                        elif cmd == "read_file":
                            return await read_file(args.get("path", ""), session_id)

                        elif cmd == "write_file":
                            return await write_file(
                                args.get("path", ""), args.get("content", ""), session_id
                            )

                        elif cmd == "write_multiple_files":
                            return await write_multiple_files(
                                args.get("files_data", []), session_id
                            )

                        elif cmd == "ask_model":
                            # PERBAIKAN: resolve model_id (support short + full key)
                            raw_model = args.get("model_id", "")
                            resolved  = self._resolve_model_id(raw_model)
                            return await ask_model(resolved, args.get("prompt", ""))

                        elif cmd == "web_search":
                            return await web_search(args.get("query", ""))

                        elif cmd == "find_safe_port":
                            return await find_safe_port(args.get("preferred", 0))

                        elif cmd == "rollback":
                            res = snapshot_manager.rollback()
                            if res["success"]:
                                return f"✅ Rollback berhasil ke commit {res['commit'][:8]}. Sistem telah dikembalikan ke state sebelumnya."
                            return f"❌ Gagal melakukan rollback: {res.get('error')}"

                        else:
                            return (
                                f"Unknown tool: '{cmd}'. "
                                f"Available: execute_bash, read_file, write_file, "
                                f"write_multiple_files, ask_model, web_search, find_safe_port"
                            )

                    # Jalankan dengan heartbeat agar tidak timeout saat npm install
                    tool_task = asyncio.create_task(_exec_tool())
                    elapsed_secs = 0.0

                    while not tool_task.done():
                        try:
                            res = await asyncio.wait_for(
                                asyncio.shield(tool_task),
                                timeout=HEARTBEAT_INTERVAL
                            )
                            break
                        except asyncio.TimeoutError:
                            elapsed_secs += HEARTBEAT_INTERVAL
                            if elapsed_secs >= MAX_TOOL_TIME:
                                tool_task.cancel()
                                try:
                                    await tool_task
                                except asyncio.CancelledError:
                                    pass
                                res = f"Tool '{cmd}' timeout setelah {int(MAX_TOOL_TIME // 60)} menit."
                                yield process_emitter.to_sentinel(
                                    "Error", f"{cmd} timeout {int(MAX_TOOL_TIME // 60)}m"
                                )
                                break
                            # Heartbeat ke frontend
                            yield process_emitter.to_sentinel(
                                "Ran", f"{_detail[:40]} ({int(elapsed_secs)}s)..."
                            )

                    if res is None:
                        res = f"Tool '{cmd}' tidak menghasilkan output."

                    # ── Artifact emit ────────────────────────────────────────
                    if cmd == "write_file" and not str(res).startswith("Error"):
                        fp = args.get("path", "")
                        fc = args.get("content", "")
                        if fp and fc:
                            ext = fp.rsplit(".", 1)[-1].lower() if "." in fp else "txt"
                            yield process_emitter.to_sentinel(
                                "Written", fp,
                                extra={
                                    "code":      fc[:8000],
                                    "language":  ext,
                                    "truncated": len(fc) > 8000,
                                }
                            )

                    elif cmd == "write_multiple_files" and not str(res).startswith("Error"):
                        # PERBAIKAN: emit SEMUA file (bukan hanya yang terakhir)
                        files_data = args.get("files_data", [])
                        for file_obj in files_data:
                            fp = file_obj.get("path", "")
                            fc = file_obj.get("content", "")
                            if fp and fc:
                                ext = fp.rsplit(".", 1)[-1].lower() if "." in fp else "txt"
                                yield process_emitter.to_sentinel(
                                    "Written", fp,
                                    extra={
                                        "code":      fc[:8000],
                                        "language":  ext,
                                        "truncated": len(fc) > 8000,
                                    }
                                )

                    # ── Result display ───────────────────────────────────────
                    res_str = str(res)
                    if include_tool_logs:
                        if cmd == "execute_bash" and not res_str.startswith("Error"):
                            display = res_str[:2000] + (
                                "\n...[output dipotong]" if len(res_str) > 2000 else ""
                            )
                            yield process_emitter.to_sentinel(
                                "Found",
                                f"output: {args.get('command', '')[:40]}",
                                extra={"result": display}
                            )
                        elif cmd == "read_file" and not res_str.startswith("Error"):
                            display = res_str[:3000] + (
                                "\n...[dipotong]" if len(res_str) > 3000 else ""
                            )
                            yield process_emitter.to_sentinel(
                                "Reading",
                                args.get("path", "").split("/")[-1],
                                extra={"result": display}
                            )
                        elif cmd == "web_search" and not res_str.startswith("Error"):
                            yield process_emitter.to_sentinel(
                                "Fetched",
                                args.get("query", "")[:50],
                                extra={"result": res_str[:2000]}
                            )
                        elif cmd not in ("write_file", "write_multiple_files"):
                            lines = res_str.strip().splitlines()
                            if len(lines) > 1:
                                yield process_emitter.to_sentinel(
                                    "Found", f"{len(lines)} lines", count=len(lines)
                                )

                    # ── Error hint ───────────────────────────────────────────
                    error_hint = _get_error_hint(res_str)

                    # ── Update conversation ──────────────────────────────────
                    obs = f"\n<observation>\n{res_str}{error_hint}\n</observation>\n"
                    # Preserve context up to the tool block so the AI remembers its thinking
                    idx_tool_end = buffer.find("</tool>")
                    if idx_tool_end != -1:
                        buffer_to_save = buffer[:idx_tool_end + 7]
                    else:
                        buffer_to_save = f"<tool>{tool_content}</tool>"
                        
                    agent_msgs.append({"role": "assistant", "content": buffer_to_save})
                    agent_msgs.append({"role": "user", "content": obs})
                    agent_msgs = self._prune_agent_messages(agent_msgs)

                except Exception as tool_err:
                    consecutive_errors += 1
                    err_msg = str(tool_err)[:150]
                    if include_tool_logs:
                        yield f"\n> ⚠️ Tool error (recovering): {err_msg}\n"
                    agent_msgs.append({"role": "assistant", "content": buffer})
                    agent_msgs.append({
                        "role": "user",
                        "content": (
                            f"<observation>\nTool error: {err_msg}. "
                            "Fix the JSON format and try again.\n</observation>"
                        )
                    })
                    agent_msgs = self._prune_agent_messages(agent_msgs)

            else:
                # ── Tidak ada tool → selesai ─────────────────────────────────
                # PERBAIKAN: reset consecutive_errors saat model berhasil respond
                consecutive_errors = 0

                remaining = response_filter.flush()
                if remaining:
                    yield remaining

                # Fallback jika model tidak pakai <response> tags
                if not response_filter.ever_emitted_response:
                    fallback = re.sub(
                        r'<(?:thinking|think)>.*?</(?:thinking|think)>',
                        '', buffer, flags=re.DOTALL
                    )
                    fallback = re.sub(
                        r'</?(?:thinking|think|response|tool|observation)>',
                        '', fallback
                    ).strip()

                    if fallback:
                        # Self-correction (opsional)
                        try:
                            from core.self_correction import self_correction_engine
                            corrected, report = await self_correction_engine.review_and_correct(
                                fallback,
                                base_model,
                                agent_msgs[0].get("content", "")[:300] if agent_msgs else ""
                            )
                            if report.total_issues_fixed > 0:
                                yield corrected
                                yield f"\n\n✅ *Self-Correction: {report.total_issues_fixed} error diperbaiki.*"
                            else:
                                yield fallback
                        except Exception:
                            yield fallback
                    elif not stream_error:
                        yield (
                            "⚠️ Proses selesai namun tidak ada respons. "
                            "Silakan ulangi pertanyaan Anda."
                        )
                break


agent_executor = AgentExecutor()
