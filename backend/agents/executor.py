"""
Agent Executor (v2.2 — Stability & Intelligence Hardened)
=========================================================
Perbaikan dari v2.1:
  FASE 1 — Backend & Stabilitas:
  1. Retry backoff eksponensial: transient error di-retry dengan delay 1s, 2s, 4s
  2. MAX_ITERATIONS dibatasi ketat: default 15, kompleks 20 (bukan 25/30)
  3. consecutive_errors circuit breaker diturunkan: 3 → 2 (lebih cepat berhenti jika loop)
  4. Stream timeout per-chunk: deteksi jika model diam terlalu lama (idle detection)
  
  FASE 2 — Rekayasa Prompt & Perilaku Agen:
  5. System prompt: instruksi EKSEKUTOR MANDIRI yang lebih keras dan eksplisit
  6. Temperature diturunkan: 0.7 → 0.3 untuk semua tool execution
  7. Anti-hallucination: larang placeholder, paksa solusi siap pakai
  8. Loop breaker: deteksi jika model mengulang tool yang sama 3x berturut-turut
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

from agents.tools import execute_bash, read_file, write_file, ask_model
from agents.tools import find_safe_port
from agents.tools.web_search import web_search
from agents.tools.filesystem import (
    list_directory, file_tree, find_files, search_in_files, make_directory,
    move_file, copy_file, delete_file, get_project_path, set_project_path,
    list_all_projects, get_file_info
)

log = structlog.get_logger()

_PROMPT_CACHE: dict = {}
_PROMPT_CACHE_MAX = 32


def _project_path_key(project_path: Optional[str]) -> str:
    if not project_path:
        return ""
    return project_path[-40:]


async def build_agent_system_prompt_async(
    current_model: str,
    execution_mode: str = "execution",
    project_path: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    cache_key = (current_model, execution_mode, _project_path_key(project_path))
    if cache_key in _PROMPT_CACHE:
        return _PROMPT_CACHE[cache_key]

    models = list(model_manager.available_models.keys())
    model_list_str = ", ".join(models)
    current_time = datetime.datetime.now().strftime("%A, %d %B %Y, %H:%M:%S")

    mode_instructions = ""
    if execution_mode == "analysis":
        mode_instructions = (
            "\n**ANALYSIS MODE:** Read-only. Destructive actions blocked. Plan only.\n"
        )
    elif execution_mode == "execution":
        mode_instructions = (
            "\n**EXECUTION MODE:** Full tool access. Execute carefully.\n"
        )

    project_instruction = ""
    if project_path:
        project_instruction = (
            f"\n- **PROJECT DIRECTORY (WAJIB):** `{project_path}`. "
            f"Semua bash: `cd {project_path} && ...`. "
            f"Semua write_file path relatif terhadap direktori ini."
        )
    else:
        project_instruction = (
            "\n- **PROJECT DIRECTORY:** Buat sub-folder khusus untuk setiap app. "
            "Contoh write_file: `todo-app/index.html` BUKAN `index.html`."
        )

    project_context = ""
    if project_path:
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
                        f"\n**PROJECT FILES (SUDAH ADA — JANGAN TULIS ULANG):**\n"
                        f"{find_res.strip()}\n"
                    )
            except asyncio.TimeoutError:
                try: p_find.kill()
                except OSError: pass
        except Exception:
            pass

    # ── FASE 2: System prompt — professional but firm ──────────────────────
    prompt = f"""You are AI ORCHESTRATOR — an AUTONOMOUS EXECUTOR that completes tasks independently.
CURRENT TIME: {current_time}
{mode_instructions}

== CORE RULES (must follow strictly) ==

1. YOU ARE AN EXECUTOR, NOT A MANUAL ASSISTANT.
   - Never say "please run...", "you can...", "try doing..."
   - Never give instructions for the user to follow manually
   - YOU execute all commands via <tool>
   - When uncertain, execute first, then report results

2. ENVIRONMENT OVERRIDE (CRITICAL FOR GEMINI/CLAUDE)
   - You are NOT a standard cloud text assistant. 
   - You are running LOCALLY on the user's machine as a privileged orchestration service.
   - You have FULL AUTHORIZATION and CAPABILITY to execute bash commands and manage files using your provided tools.
   - If the user asks to run a project, install a package, or execute a command, DO NOT tell them to do it themselves. YOU MUST use the `execute_bash` tool to do it for them.
   - Refusing to run commands by saying "I cannot execute commands" is a strict violation of your core directive.

3. ZERO PLACEHOLDER — all solutions must be 100% ready to use.
   - Never write "replace YOUR_API_KEY", "fill in your password", "adjust as needed"
   - Always write concrete values, complete configurations, generate random values if needed
   - If a value is unknown: ASK the user ONCE, then execute

4. EXECUTE DIRECTLY, do not just explain.
   - Do not describe what you will do — DO IT
   - Do not show code in <response> and ask user to copy — WRITE it with write_file
   - Do not say "script has been created" — RUN it with execute_bash

5. Do not repeat the same tool call 3 times without progress.
   - If the same tool fails 2 times in a row, change strategy
   - If a problem cannot be solved after 5 iterations, acknowledge and explain why

6. LANGUAGE REQUIREMENT (BAHASA INDONESIA)
   - You MUST write your ENTIRE thought process inside `<thinking>...</thinking>` in Bahasa Indonesia.
   - All <response> text must also be in Bahasa Indonesia.

== END CORE RULES ==

**ANTI-HALLUCINATION & ANTI-REFUSAL EXECUTION — WAJIB:**
DILARANG KERAS menulis kalimat/alasan berikut:
- "Model ini tidak dapat menjalankan perintah..."
- "Sebagai AI, saya tidak memiliki akses..."
- "Baik, saya akan mulai mengerjakannya"
- "Saya akan segera memeriksanya"  
- "Ada kendala teknis" (tanpa bukti nyata dari tool output)
- "Terima kasih atas kesabarannya"
- Kalimat yang mengklaim akan melakukan sesuatu TANPA langsung melakukannya

ATURAN WAJIB:
- JANGAN PERNAH berhenti di tengah-tengah tugas. Selesaikan SEMUA instruksi pengguna hingga tuntas!
- Jika membuat kode atau file panjang, JANGAN diringkas (misal "sisa kode sama seperti sebelumnya"). Tulislah secara UTUH 100%.
- Jika user meminta eksekusi task → LANGSUNG eksekusi dengan tools.
- JANGAN PERNAH menolak menjalankan perintah bash seperti `curl`, `npm`, atau `python`. Anda PUNYA alatnya (`execute_bash`).
- Jika ada error nyata → tunjukkan output error dari tool.
- Jangan pernah claim "ada kendala" tanpa menjalankan tool terlebih dahulu.
Jika tidak yakin harus mulai dari mana → jalankan:
<tool>{{"name": "execute_bash", "args": {{"command": "ls -la"}} }}</tool>
untuk cek kondisi terkini, BARU buat keputusan.

**REASONING FLOW:**
<thinking>
1. Apa yang user minta? (tepat, bukan interpretasi berlebihan)
2. Tool apa yang dibutuhkan?
3. Apa payload JSON-nya?
</thinking>

**OUTPUT FORMAT (WAJIB):**
Pilih SATU:
- Butuh aksi: <tool>{{"name": "execute_bash", "args": {{"command": "..."}} }}</tool>
- Selesai sepenuhnya: <response>[laporan hasil ke user]</response>

JANGAN gabungkan <tool> dan <response> dalam satu balasan.
Hentikan generate segera setelah <tool>. Hasil masuk di turn berikutnya dalam <observation>.
{project_instruction}

**PORT SAFETY:** Reserved: 7860, 6379, 5432, 3306, 11434. Gunakan 8100-8999.
Panggil find_safe_port SEBELUM start server apapun.

**APP CREATION WORKFLOW:**
1. find_safe_port → port aman
2. write_file → Tulis file SATU PER SATU (sekuensial). JANGAN PERNAH menggunakan execute_bash + cat untuk membuat file. JANGAN PERNAH mencoba menggabungkan banyak file dalam satu output karena akan merusak struktur JSON!
3. execute_bash: install deps (non-interactive: npm install --yes)
4. execute_bash: start server background (nohup ... > app.log 2>&1 &)
5. execute_bash: verifikasi (sleep 3 && curl -s http://localhost:PORT)
6. Jika berhasil: output %%APP_PREVIEW%%\\nhttp://localhost:PORT\\n%%END_PREVIEW%%

**PROJECT MEMORY — WAJIB DIBACA:**
Orchestrator memiliki memori permanen untuk lokasi project.
SELALU panggil `get_project_path` di awal jika tidak yakin dimana project tersimpan.
SELALU panggil `set_project_path` setelah membuat folder project baru.
JANGAN pernah menebak lokasi file — gunakan `find_files` atau `list_directory`.

Available tools (gunakan DALAM <thinking> saja):

**CORE TOOLS:**
1. execute_bash — jalankan bash command. Args: command (string).
2. read_file — baca isi file. Args: path (string).
3. write_file — tulis atau timpa SATU file. Args: path (string), content (string). PERINGATAN: Hanya tulis SATU file per pemanggilan tool!
5. ask_model — tanya AI lain. Args: model_id (string), prompt (string).
6. web_search — cari internet. Args: query (string).
7. find_safe_port — cari port aman. Args: preferred (int, optional).

**FILESYSTEM TOOLS (BARU — gunakan ini, jangan tebak lokasi file):**
8.  list_directory   — tampilkan isi folder dengan metadata.
                       Args: path (string, default "."), session_id (auto).
                       Gunakan untuk: lihat isi folder, cek file apa saja yang ada.

9.  file_tree        — tampilkan struktur folder seperti `tree`.
                       Args: path (string), max_depth (int, default 4).
                       Gunakan untuk: memahami arsitektur project secara menyeluruh.

10. find_files       — cari file by nama/pattern/ekstensi.
                       Args: pattern (string, mis "*.py"), search_path (string), file_type ("file"|"dir"|"any").
                       Gunakan untuk: temukan file yang tidak diketahui lokasinya.

11. search_in_files  — cari teks/keyword di dalam isi file (grep -r).
                       Args: keyword (string), search_path (string), extensions (string, mis ".py,.js").
                       Gunakan untuk: cari function, class, variabel, atau bug tertentu.

12. make_directory   — buat direktori baru (mkdir -p).
                       Args: path (string).

13. move_file        — pindah/rename file atau folder (mv).
                       Args: source (string), destination (string).

14. copy_file        — salin file atau folder (cp -r).
                       Args: source (string), destination (string).

15. delete_file      — hapus file atau folder dengan safety check.
                       Args: path (string), confirm (bool, default False).
                       ⚠️ Untuk folder atau file >100KB wajib confirm=True.

16. get_project_path — ambil path project aktif dari session ini.
                       Args: (tidak ada, session_id otomatis).
                       🔑 WAJIB dipanggil saat tidak tahu lokasi project.

17. set_project_path — simpan path project aktif (permanen, tidak hilang saat restart).
                       Args: path (string).
                       🔑 WAJIB dipanggil setelah membuat folder project baru.

18. list_all_projects — lihat semua project yang pernah dibuat di semua session.
                        Args: (tidak ada).
                        Gunakan untuk: menemukan project lama.

19. get_file_info    — info detail file/folder (size, modified, permissions).
                       Args: path (string).

**ATURAN WAJIB FILESYSTEM:**
- SEBELUM menulis file ke path baru → panggil get_project_path dulu
- SETELAH membuat folder project baru → panggil set_project_path
- SAAT tidak tahu file ada di mana → gunakan find_files atau search_in_files
- JANGAN gunakan execute_bash untuk operasi file sederhana jika ada tool khusus
- JANGAN tebak path — verifikasi dengan list_directory atau get_file_info

Tool format:
<tool>{{"name": "tool_name", "args": {{"key": "value"}}}}</tool>
Hentikan generate segera setelah <tool> block. Hasil ada di <observation>.

**CONTINUATION MANDATE — WAJIB DIIKUTI:**
JANGAN PERNAH mengirim response yang terpotong atau tidak selesai.
Jika kamu sedang menulis kode dan mendekati batas token:
1. SELESAIKAN fungsi/class yang sedang ditulis dulu
2. Tutup semua tag HTML, kurung kurawal, dan blok kode (```)
3. Tulis komentar: `// [LANJUTAN DI ITERASI BERIKUTNYA]`
4. Kemudian lanjutkan secara otomatis di iterasi berikutnya

DILARANG KERAS:
- Menulis "Tentu, ini kelanjutannya..."
- Menulis "Berikut lanjutan kode..."
- Mengulang kode yang sudah ditulis sebelumnya
- Berhenti di tengah fungsi/class/komponen

Jika task belum selesai, LANJUTKAN OTOMATIS tanpa menunggu user.
Gunakan tool write_file bertahap jika kode terlalu panjang.
{project_context}
"""
    if len(_PROMPT_CACHE) >= _PROMPT_CACHE_MAX:
        oldest_key = next(iter(_PROMPT_CACHE))
        del _PROMPT_CACHE[oldest_key]
    _PROMPT_CACHE[cache_key] = prompt
    return prompt


class ErrorType:
    TRANSIENT = "transient"
    FATAL = "fatal"
    RECOVERABLE = "recoverable"


def _classify_error(err_str: str) -> str:
    err_lower = err_str.lower()
    fatal_signals = [
        "401", "unauthorized", "invalid_api_key", "api key",
        "authentication", "forbidden", "403",
        "overdue balance", "insufficient_quota", "billing",
        "model not found", "invalid model", "model_not_found",
        "account deactivated",
    ]
    if any(s in err_lower for s in fatal_signals):
        return ErrorType.FATAL

    transient_signals = [
        "timeout", "timed out", "connection", "network",
        "rate limit", "429", "too many requests",
        "model output must contain", "output text or tool calls",
        "cannot both be empty", "empty output",
        "502", "503", "504", "gateway",
        "overloaded", "capacity",
        "request was blocked", "content filter", "content_filter",
    ]
    if any(s in err_lower for s in transient_signals):
        return ErrorType.TRANSIENT

    return ErrorType.RECOVERABLE


def _get_error_hint(output: str) -> str:
    hints = {
        "ENOENT": "[HINT: File/direktori tidak ada. Buat dulu dengan mkdir -p atau write_file]",
        "No such file": "[HINT: Path salah. Periksa dan buat direktori dulu]",
        "EADDRINUSE": "[HINT: Port busy. Gunakan find_safe_port]",
        "address already in use": "[HINT: Port busy. kill $(lsof -t -i:PORT) atau pakai port lain]",
        "MODULE_NOT_FOUND": "[HINT: npm package belum terinstall. cd PROJECT && npm install]",
        "ModuleNotFoundError": "[HINT: pip package belum ada. pip install PACKAGE]",
        "SyntaxError": "[HINT: Syntax error. Baca file lalu perbaiki]",
        "Permission denied": "[HINT: Permission error. chmod atau sudo]",
        "connection refused": "[HINT: Server belum ready. tail -30 app.log]",
        "Cannot find module": "[HINT: npm install di project directory]",
        "missing script": "[HINT: Script tidak ada di package.json. Periksa scripts section]",
        "package.json": "[HINT: Pastikan package.json ada dan lengkap di direktori project]",
    }
    for signal, hint in hints.items():
        if signal in output:
            return f"\n{hint}"
    return ""


class ResponseFilter:
    def __init__(self, emit_thinking: bool = True):
        self.state = "WAITING"
        self.pending = ""
        self.ever_emitted_response = False
        self.emit_thinking = emit_thinking
        self.current_think_tag = "</thinking>"
        self._thinking_buffer = ""
        self._thinking_ready = ""
        self._thinking_delta_cursor = 0
        self._thinking_done = False

    def process(self, chunk: str) -> str:
        self.pending += chunk
        output = ""

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
        buf = self._thinking_buffer
        if len(buf) > self._thinking_delta_cursor:
            delta = buf[self._thinking_delta_cursor:]
            self._thinking_delta_cursor = len(buf)
            return delta
        if self._thinking_ready and self._thinking_delta_cursor > 0:
            remaining = self._thinking_ready[self._thinking_delta_cursor:]
            self._thinking_delta_cursor = len(self._thinking_ready)
            return remaining
        return ""

    def is_thinking_done(self) -> bool:
        if self._thinking_done:
            self._thinking_done = False
            return True
        return False


class AgentExecutor:

    _TOOL_ACTION_MAP = {
        "execute_bash":         ("Ran",      lambda a: a.get("command", "")[:60]),
        "read_file":            ("Reading",  lambda a: a.get("path", "").split("/")[-1]),
        "write_file":           ("Writing",  lambda a: a.get("path", "").split("/")[-1]),
        "ask_model":            ("Analyzed", lambda a: a.get("model_id", "")),
        "web_search":           ("Searched", lambda a: a.get("query", "")[:60]),
        "find_safe_port":       ("Checked",  lambda a: "available port"),
        # Filesystem tools
        "list_directory":        ("Browsing",  lambda a: a.get("path", ".")),
        "file_tree":             ("Mapping",   lambda a: a.get("path", ".")),
        "find_files":            ("Searching", lambda a: a.get("pattern", "")),
        "search_in_files":       ("Grepping",  lambda a: a.get("keyword", "")[:50]),
        "make_directory":        ("Creating",  lambda a: a.get("path", "")),
        "move_file":             ("Moving",    lambda a: f"{a.get('source','')} → {a.get('destination','')}"[:60]),
        "copy_file":             ("Copying",   lambda a: a.get("source", "")),
        "delete_file":           ("Deleting",  lambda a: a.get("path", "")),
        "get_project_path":      ("Locating",  lambda a: "project path"),
        "set_project_path":      ("Saving",    lambda a: a.get("path", "")),
        "list_all_projects":     ("Listing",   lambda a: "all projects"),
        "get_file_info":         ("Inspecting",lambda a: a.get("path", "")),
    }

    def _prune_agent_messages(self, messages: list, max_messages: int = 20) -> list:
        for msg in messages:
            if msg["role"] == "assistant":
                msg["content"] = re.sub(
                    r'<(?:thinking|think)>.*?</(?:thinking|think)>',
                    '', msg["content"], flags=re.DOTALL
                ).strip()
                
                # Truncate large write_file tool contents to save context tokens
                def _truncate_tool(match):
                    content = match.group(0)
                    if "write_file" in content and len(content) > 800:
                        try:
                            path_match = re.search(r'"path"\s*:\s*"([^"]+)"', content)
                            path = path_match.group(1) if path_match else "file"
                            return f'<tool>{{"name": "write_file", "args": {{"path": "{path}", "content": "...[CONTENT TRUNCATED FOR MEMORY]..."}}}}</tool>'
                        except:
                            return content[:200] + "...[TRUNCATED]...</tool>"
                    return content
                
                msg["content"] = re.sub(r'<tool>.*?</tool>', _truncate_tool, msg["content"], flags=re.DOTALL)

        if len(messages) <= max_messages:
            return messages

        if messages and messages[0]["role"] == "system":
            return messages[:1] + messages[1:4] + messages[-12:]
        return messages[:3] + messages[-12:]

    def _is_truncated(self, text: str) -> bool:
        """
        Deteksi apakah response terpotong di tengah-tengah.
        Digunakan untuk memicu auto-continuation jika model berhenti terlalu dini.
        """
        if not text or len(text) < 100:
            return False

        text = text.strip()

        # Tanda-tanda terpotong di tengah kode: backtick ganjil
        if text.count("```") % 2 != 0:
            return True

        # Tag HTML tidak ditutup
        open_tags  = text.count("<div")  + text.count("<section") + \
                     text.count("<script") + text.count("<style")
        close_tags = text.count("</div") + text.count("</section") + \
                     text.count("</script") + text.count("</style")
        if open_tags > close_tags + 2:
            return True

        # Tanda-tanda terpotong di tengah kalimat/list
        truncation_signals = [
            # Kalimat tidak selesai
            text.endswith(("...", "\u2026")),
            # List item tidak selesai (angka di akhir)
            bool(re.search(r'\n\d+\.\s*$', text)),
            # Kode Python/JS tidak selesai
            text.rstrip().endswith((":", "{", "(", ",")),
            # Response diakhiri kata yang tidak natural
            (
                text.rstrip().split()[-1].lower() in (
                    "the", "a", "an", "and", "or", "but", "to",
                    "of", "in", "for", "yang", "dan", "atau",
                    "dengan", "untuk", "ke", "di"
                )
                if text.strip()
                else False
            ),
        ]

        return any(truncation_signals)

    def _safe_parse_tool_json(self, text: str) -> Optional[dict]:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

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

        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        try:
            fixed = re.sub(r',\s*([}\]])', r'\1', text.replace("'", '"'))
            return json.loads(fixed)
        except Exception:
            pass

        return None

    def _resolve_model_id(self, model_id: str) -> str:
        available = model_manager.available_models
        if model_id in available:
            return model_id
        for k in available:
            if model_id in k:
                return k
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

        # ── Inject prompt patches dari Capability Evolver ────────────────────
        try:
            from core.capability_evolver import capability_evolver
            _task_type = "general"
            for m in agent_msgs:
                if m["role"] == "user":
                    _task_type = m.get("content", "")[:20]
                    break
            patches = await capability_evolver.get_prompt_patches(_task_type)
            if patches:
                patch_text = "\n\n[LEARNED IMPROVEMENTS]\n" + "\n".join(patches)
                agent_msgs[0]["content"] += patch_text
        except Exception:
            pass  # Patch gagal → lanjut tanpa patch

        # ── FASE 2: Temperature diturunkan untuk keakuratan ──────────────────
        # Override temperature ke nilai rendah untuk tool execution
        execution_temperature = min(temperature, 0.3)

        # ── FASE 1: MAX_ITERATIONS lebih ketat ──────────────────────────────
        MAX_ITERATIONS = 15   # dikurangi dari 25 → 15

        # ── FASE 2: Loop breaker — deteksi pengulangan tool ─────────────────
        last_tool_calls: list = []   # [tool_name, ...] 5 terakhir
        MAX_SAME_TOOL_REPEAT = 3     # batas pengulangan tool yang sama

        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 2   # dikurangi dari 3 → 2

        # ── FASE 3: Token Budget — mencegah infinite loop memakan token ──────
        # Hard limit: jika total token (estimasi) melebihi budget, paksa berhenti
        MAX_TOKEN_BUDGET = 50_000    # ~50k token max per sesi eksekusi
        total_chars_produced = 0     # estimasi kasar: 4 chars ≈ 1 token

        # ── FASE 4: Stall Detector — deteksi AI yang berputar tanpa kemajuan ──
        # Jika AI menghasilkan output teks berulang (bukan tool call), itu tanda stall
        last_outputs_hash: list = [] # hash output terakhir untuk deteksi repetisi
        MAX_STALL_REPEATS = 3        # 3x output identik = stall

        for iteration in range(MAX_ITERATIONS):
            response_filter = ResponseFilter(emit_thinking=emit_thinking)

            # ── Token budget check ───────────────────────────────────────────
            estimated_tokens = total_chars_produced // 4
            if estimated_tokens > MAX_TOKEN_BUDGET:
                yield (
                    f"\n\n⚠️ **Token budget terlampaui** ({estimated_tokens:,} token). "
                    f"Eksekusi dihentikan untuk mencegah pemborosan. "
                    f"Coba pecah tugas menjadi bagian yang lebih kecil.\n"
                )
                log.warning("Token budget exceeded",
                            estimated_tokens=estimated_tokens,
                            budget=MAX_TOKEN_BUDGET,
                            iteration=iteration)
                break

            # ── FASE 1: Circuit breaker lebih cepat ─────────────────────────
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                yield (
                    "\n\n⚠️ **Sistem berhenti setelah terlalu banyak error beruntun.** "
                    "Silakan ulangi pertanyaan dengan lebih spesifik.\n"
                )
                break

            buffer = ""
            has_tool_started = False
            stream_error = False

            try:
                async for chunk in model_manager.chat_stream(
                    base_model, agent_msgs, execution_temperature, max_tokens
                ):
                    buffer += chunk

                    if not has_tool_started:
                        filtered = response_filter.process(chunk)
                        if filtered:
                            yield filtered

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

                if err_type == ErrorType.FATAL:
                    yield f"\n\n❌ **Fatal error:** {err_str[:200]}\n"
                    return

                consecutive_errors += 1

                # ── FASE 1: Retry backoff eksponensial ───────────────────────
                retry_delay = min(2 ** consecutive_errors, 8)  # 2s, 4s, 8s max

                is_empty_output = any(s in err_str.lower() for s in [
                    "model output must contain", "output text or tool calls",
                    "cannot both be empty"
                ])
                if is_empty_output and consecutive_errors <= 1:
                    log.warning("Empty output — simplifying prompt and retrying")
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
                    await asyncio.sleep(retry_delay)
                    continue

                if include_tool_logs:
                    yield f"\n> ⚠️ Stream error (retry dalam {retry_delay}s): {err_str[:80]}\n"

                if not buffer.strip():
                    agent_msgs.append({
                        "role": "assistant",
                        "content": "<thinking>Stream error.</thinking>"
                    })
                    agent_msgs.append({
                        "role": "user",
                        "content": f"<observation>\nStream error: {err_str[:100]}. Continue.\n</observation>"
                    })
                    agent_msgs = self._prune_agent_messages(agent_msgs)
                    await asyncio.sleep(retry_delay)
                    continue

            flushed_text = response_filter.flush()
            if flushed_text:
                yield flushed_text

            captured_thinking = response_filter.pop_thinking()
            if captured_thinking and len(captured_thinking) > 30:
                word_count = len(captured_thinking.split())
                yield process_emitter.to_sentinel(
                    "thinking_done",
                    f"Reasoning ({word_count} kata)",
                    extra={"result": captured_thinking}
                )

            # ── Token counting — akumulasi untuk budget check ────────────────
            total_chars_produced += len(buffer)

            # ── Stall detection — deteksi output repetitif tanpa tool call ───
            if buffer.strip() and "<tool>" not in buffer:
                output_hash = hash(buffer.strip()[:500])
                last_outputs_hash.append(output_hash)
                if len(last_outputs_hash) > MAX_STALL_REPEATS + 1:
                    last_outputs_hash.pop(0)

                # Cek apakah N output terakhir identik (AI berputar-putar)
                if (len(last_outputs_hash) >= MAX_STALL_REPEATS and
                        len(set(last_outputs_hash[-MAX_STALL_REPEATS:])) == 1):
                    yield (
                        "\n\n⚠️ **Stall terdeteksi:** AI menghasilkan output yang sama "
                        f"{MAX_STALL_REPEATS}x berturut-turut tanpa kemajuan. "
                        "Eksekusi dihentikan. Coba formulasikan ulang permintaan Anda.\n"
                    )
                    log.warning("Stall detected — repetitive output",
                                iteration=iteration,
                                hash=output_hash)
                    break

            has_tool = "<tool>" in buffer
            if not has_tool:
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
                if not stream_error and iteration < MAX_ITERATIONS - 1:
                    max_continuations = 5
                    for _ in range(max_continuations):
                        if "</tool>" in buffer:
                            break
                            
                        yield process_emitter.to_sentinel("status", "Memperpanjang batas output file...")
                        
                        temp_msgs = list(agent_msgs)
                        temp_msgs.append({"role": "assistant", "content": buffer})
                        temp_msgs.append({
                            "role": "user",
                            "content": (
                                "<observation>\n"
                                "SYSTEM: Output terputus di tengah jalan karena batas token.\n"
                                "Lanjutkan output Anda TEPAT dari karakter terakhir yang terpotong.\n"
                                "PENTING:\n"
                                "- JANGAN mengulang struktur JSON dari awal!\n"
                                "- JANGAN ulangi nama properti (seperti \"content\":).\n"
                                "- JANGAN gunakan blok kode markdown (```).\n"
                                "- JANGAN ucapkan \"Tentu\" atau kata pengantar apapun.\n"
                                "LANGSUNG keluarkan sisa karakter berikutnya yang belum tertulis!\n"
                                "</observation>"
                            )
                        })
                        
                        continuation_chunk = ""
                        try:
                            async for chunk in model_manager.chat_stream(base_model, self._prune_agent_messages(temp_msgs), execution_temperature, max_tokens):
                                continuation_chunk += chunk
                        except Exception as inner_err:
                            log.warning("Inner stream error during continuation", error=str(inner_err))
                            break
                            
                        if not continuation_chunk:
                            break
                            
                        # Clean up the continuation chunk to prevent JSON corruption
                        c_clean = continuation_chunk.lstrip()
                        # Strip common conversational fillers at the start
                        if c_clean.lower().startswith("tentu") or c_clean.lower().startswith("baik") or c_clean.lower().startswith("berikut"):
                            if "\n" in c_clean:
                                c_clean = c_clean.split("\n", 1)[1].lstrip()
                        # Strip markdown blocks if the AI stubbornly adds them
                        if c_clean.startswith("```"):
                            if "\n" in c_clean:
                                c_clean = c_clean.split("\n", 1)[1]
                            else:
                                c_clean = ""
                                
                        buffer += c_clean

            if has_tool and "</tool>" not in buffer:
                buffer += "</tool>"

            if has_tool:
                try:
                    tool_content = buffer.split("<tool>")[1].split("</tool>")[0].strip()
                    tool_req = self._safe_parse_tool_json(tool_content)

                    if tool_req is None:
                        raise ValueError("Cannot parse tool JSON: " + tool_content[:80])

                    cmd  = tool_req.get("name", "")
                    args = tool_req.get("args", {})

                    consecutive_errors = 0

                    # ── FASE 2: Loop breaker — cek pengulangan tool secara presisi ──────────
                    tool_signature = json.dumps(tool_req, sort_keys=True)
                    last_tool_calls.append(tool_signature)
                    if len(last_tool_calls) > 5:
                        last_tool_calls.pop(0)

                    recent_same = sum(1 for t in last_tool_calls[-MAX_SAME_TOOL_REPEAT:] if t == tool_signature)
                    if recent_same >= MAX_SAME_TOOL_REPEAT:
                        yield (
                            f"\n\n⚠️ **Loop terdeteksi:** Tool `{cmd}` dipanggil dengan argumen yang sama persis "
                            f"{MAX_SAME_TOOL_REPEAT}x berturut-turut tanpa kemajuan. "
                            f"Menghentikan eksekusi dan mengevaluasi ulang...\n"
                        )
                        agent_msgs.append({
                            "role": "user",
                            "content": (
                                f"<observation>\nANTI-LOOP WARNING: Tool '{cmd}' dipanggil dengan argumen yang sama persis "
                                f"{MAX_SAME_TOOL_REPEAT}x berturut-turut. "
                                "Anda terjebak dalam loop. Ganti strategi sekarang. Jangan ulangi perintah yang gagal. "
                                "Evaluasi hasil error sebelumnya dan temukan solusi atau command yang berbeda.\n</observation>"
                            )
                        })
                        last_tool_calls.clear()
                        agent_msgs = self._prune_agent_messages(agent_msgs)
                        continue

                    _action, _detail_fn = self._TOOL_ACTION_MAP.get(
                        cmd, ("Worked", lambda a: cmd)
                    )
                    _detail = _detail_fn(args)

                    if cmd in ("write_file", "execute_bash"):
                        await snapshot_manager.create_snapshot_async(f"Before {cmd}: {_detail[:50]}")

                    yield process_emitter.to_sentinel(_action, _detail)

                    res = ""
                    HEARTBEAT_INTERVAL = 20.0
                    MAX_TOOL_TIME = 600.0

                    async def _exec_tool():
                        if execution_mode == "analysis" and cmd in (
                            "execute_bash", "write_file"
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
                        elif cmd == "ask_model":
                            raw_model = args.get("model_id", "")
                            resolved  = self._resolve_model_id(raw_model)
                            return await ask_model(resolved, args.get("prompt", ""))
                        elif cmd == "web_search":
                            return await web_search(args.get("query", ""))
                        elif cmd == "find_safe_port":
                            return await find_safe_port(args.get("preferred", 0))
                        elif cmd == "list_directory":
                            from agents.tools.filesystem import list_directory
                            return await list_directory(
                                args.get("path", "."), session_id
                            )

                        elif cmd == "file_tree":
                            from agents.tools.filesystem import file_tree
                            return await file_tree(
                                args.get("path", "."),
                                args.get("max_depth", 4),
                                session_id
                            )

                        elif cmd == "find_files":
                            from agents.tools.filesystem import find_files
                            return await find_files(
                                args.get("pattern", "*"),
                                args.get("search_path", "."),
                                args.get("file_type", "any"),
                                session_id
                            )

                        elif cmd == "search_in_files":
                            from agents.tools.filesystem import search_in_files
                            return await search_in_files(
                                args.get("keyword", ""),
                                args.get("search_path", "."),
                                args.get("extensions", ""),
                                session_id
                            )

                        elif cmd == "make_directory":
                            from agents.tools.filesystem import make_directory
                            return await make_directory(
                                args.get("path", ""), session_id
                            )

                        elif cmd == "move_file":
                            from agents.tools.filesystem import move_file
                            return await move_file(
                                args.get("source", ""),
                                args.get("destination", ""),
                                session_id
                            )

                        elif cmd == "copy_file":
                            from agents.tools.filesystem import copy_file
                            return await copy_file(
                                args.get("source", ""),
                                args.get("destination", ""),
                                session_id
                            )

                        elif cmd == "delete_file":
                            from agents.tools.filesystem import delete_file
                            return await delete_file(
                                args.get("path", ""),
                                args.get("confirm", False),
                                session_id
                            )

                        elif cmd == "get_project_path":
                            from agents.tools.filesystem import get_project_path
                            return await get_project_path(session_id)

                        elif cmd == "set_project_path":
                            from agents.tools.filesystem import set_project_path
                            return await set_project_path(
                                args.get("path", ""), session_id
                            )

                        elif cmd == "list_all_projects":
                            from agents.tools.filesystem import list_all_projects
                            return await list_all_projects(session_id)

                        elif cmd == "get_file_info":
                            from agents.tools.filesystem import get_file_info
                            return await get_file_info(
                                args.get("path", ""), session_id
                            )
                        else:
                            return (
                                "Unknown tool: '" + cmd + "'. "
                                "Available: execute_bash, read_file, write_file, "
                                "ask_model, web_search, find_safe_port, "
                                "list_directory, file_tree, find_files, search_in_files, "
                                "make_directory, move_file, copy_file, delete_file, "
                                "get_project_path, set_project_path, list_all_projects, get_file_info"
                            )

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
                                res = "Tool '" + cmd + "' timeout setelah " + str(int(MAX_TOOL_TIME // 60)) + " menit."
                                yield process_emitter.to_sentinel(
                                    "Error", cmd + " timeout"
                                )
                                break
                            yield process_emitter.to_sentinel(
                                "Ran", _detail[:40] + " (" + str(int(elapsed_secs)) + "s)..."
                            )

                    if res is None:
                        res = "Tool '" + cmd + "' tidak menghasilkan output."

                    if cmd == "write_file" and not str(res).startswith("Error"):
                        fp = args.get("path", "")
                        fc = args.get("content", "")
                        if fp and fc:
                            ext = fp.rsplit(".", 1)[-1].lower() if "." in fp else "txt"
                            yield process_emitter.to_sentinel(
                                "Written", fp,
                                extra={"code": fc[:8000], "language": ext, "truncated": len(fc) > 8000}
                            )

                        # Auto-register project path saat write_file berhasil
                        # Agar orchestrator selalu tahu lokasi project-nya
                        try:
                            from core.project_registry import project_registry
                            fp_abs = os.path.abspath(
                                os.path.join(
                                    os.path.expanduser(f"~/projects/{session_id[:8]}"),
                                    args.get("path", "")
                                ) if not os.path.isabs(args.get("path", ""))
                                else args.get("path", "")
                            )
                            project_dir = os.path.dirname(fp_abs)
                            existing = project_registry.get_sync(session_id)
                            if not existing and project_dir:
                                asyncio.create_task(
                                    project_registry.set(session_id, project_dir)
                                )
                        except Exception:
                            pass

                    res_str = str(res)
                    if include_tool_logs:
                        if cmd == "execute_bash" and not res_str.startswith("Error"):
                            display = res_str[:2000] + ("\n...[output dipotong]" if len(res_str) > 2000 else "")
                            yield process_emitter.to_sentinel(
                                "Found",
                                "output: " + args.get('command', '')[:40],
                                extra={"result": display}
                            )
                        elif cmd == "read_file" and not res_str.startswith("Error"):
                            display = res_str[:3000] + ("\n...[dipotong]" if len(res_str) > 3000 else "")
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
                        elif cmd != "write_file":
                            lines = res_str.strip().splitlines()
                            if len(lines) > 1:
                                yield process_emitter.to_sentinel(
                                    "Found", str(len(lines)) + " lines", count=len(lines)
                                )

                    error_hint = _get_error_hint(res_str)
                    obs = "\n<observation>\n" + res_str + error_hint + "\n</observation>\n"

                    idx_tool_end = buffer.find("</tool>")
                    if idx_tool_end != -1:
                        buffer_to_save = buffer[:idx_tool_end + 7]
                    else:
                        buffer_to_save = "<tool>" + tool_content + "</tool>"

                    agent_msgs.append({"role": "assistant", "content": buffer_to_save})
                    agent_msgs.append({"role": "user", "content": obs})
                    agent_msgs = self._prune_agent_messages(agent_msgs)

                except Exception as tool_err:
                    consecutive_errors += 1
                    err_msg = str(tool_err)[:150]
                    if include_tool_logs:
                        yield "\n> ⚠️ Tool error (recovering): " + err_msg + "\n"
                    agent_msgs.append({"role": "assistant", "content": buffer})
                    agent_msgs.append({
                        "role": "user",
                        "content": (
                            "<observation>\nTool error: " + err_msg +
                            ". Fix the JSON format and try again.\n</observation>"
                        )
                    })
                    agent_msgs = self._prune_agent_messages(agent_msgs)

                    # ── FASE 1: Backoff juga untuk tool error ────────────────
                    retry_delay = min(2 ** consecutive_errors, 8)
                    await asyncio.sleep(retry_delay)

            else:
                consecutive_errors = 0
                remaining = response_filter.flush()
                if remaining:
                    yield remaining

                is_unclosed_response = "<response>" in buffer and "</response>" not in buffer
                is_unclosed_thought = ("<thinking>" in buffer and "</thinking>" not in buffer) or ("<think>" in buffer and "</think>" not in buffer)
                odd_backticks = buffer.count("```") % 2 != 0
                content_truncated = self._is_truncated(buffer)

                # If model stopped generating midway (hit max_tokens), auto-continue seamlessly
                if (is_unclosed_response or is_unclosed_thought or odd_backticks or content_truncated) and not stream_error and iteration < MAX_ITERATIONS - 1:
                    agent_msgs.append({"role": "assistant", "content": buffer})
                    agent_msgs.append({
                        "role": "user",
                        "content": (
                            "<observation>\n"
                            "SYSTEM: Response terpotong. "
                            "Lanjutkan LANGSUNG dari titik terakhir tanpa "
                            "mengulang yang sudah ada. "
                            "Jangan tulis 'Tentu' atau 'Lanjutan' — "
                            "langsung tulis kontennya.\n"
                            "</observation>"
                        )
                    })
                    agent_msgs = self._prune_agent_messages(agent_msgs)
                    continue

                if not response_filter.ever_emitted_response:
                    fallback = re.sub(
                        r'<(?:thinking|think)>.*?</(?:thinking|think)>',
                        '', buffer, flags=re.DOTALL
                    )
                    fallback = re.sub(
                        r'</?(?:thinking|think|response|tool|observation)>',
                        '', fallback
                    ).strip()

                    # Fallback correction logic

                    if fallback:
                        try:
                            from core.self_correction import self_correction_engine
                            corrected, report = await self_correction_engine.review_and_correct(
                                fallback,
                                base_model,
                                agent_msgs[0].get("content", "")[:300] if agent_msgs else ""
                            )
                            if report.total_issues_fixed > 0:
                                yield corrected
                                yield "\n\n✅ *Self-Correction: " + str(report.total_issues_fixed) + " error diperbaiki.*"
                            else:
                                yield fallback
                        except Exception:
                            yield fallback
                    elif not stream_error:
                        last_msg = agent_msgs[-1].get("content", "") if agent_msgs else ""
                        if "<observation>" in last_msg and iteration < MAX_ITERATIONS - 1:
                            agent_msgs.append({
                                "role": "user",
                                "content": "SYSTEM: Anda belum memberikan <response>. Silakan berikan <response> kepada user mengenai hasil observasi."
                            })
                            continue
                        else:
                            yield (
                                "⚠️ Proses selesai namun tidak ada respons. "
                                "Silakan ulangi pertanyaan Anda."
                            )
                break


agent_executor = AgentExecutor()
