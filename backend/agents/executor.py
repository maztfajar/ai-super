import json
import re
import asyncio
from typing import AsyncGenerator
import structlog
from core.model_manager import model_manager
from core.smart_router import smart_router
from core.process_emitter import process_emitter, PROCESS_EVENT_PREFIX
from agents.tools import execute_bash, read_file, write_file, ask_model
from agents.tools.web_search import web_search

log = structlog.get_logger()

def build_agent_system_prompt(current_model: str, execution_mode: str = "execution", project_path: str = None, session_id: str = None) -> str:
    from core.model_manager import model_manager
    import datetime

    models = list(model_manager.available_models.keys())
    model_list_str = ", ".join(models)
    
    # Get current datetime to prevent models from rejecting future dates (e.g., cutoff in 2023 but current is 2026)
    current_time = datetime.datetime.now().strftime("%A, %d %B %Y, %H:%M:%S")
    
    mode_instructions = ""
    if execution_mode == "analysis":
        mode_instructions = "\n**ANALYSIS MODE ACTIVE:** You are in read-only analysis mode. Destructive actions (execute_bash, write_file) will be simulated or blocked. Focus on understanding and planning.\n"
    elif execution_mode == "execution":
        mode_instructions = "\n**EXECUTION MODE ACTIVE:** You have full permission to use tools. Execute your plan carefully, but do not destroy the system.\n"
        
    project_instruction = ""
    if project_path:
        project_instruction = f"""
- **PROJECT DIRECTORY (CRITICAL):** The user has EXPLICITLY set the working directory to `{project_path}`. You MUST execute all your bash commands (`cd {project_path} && ...`) and create all files (`write_file` path should be relative to this or absolute within it) inside this directory. NEVER write files to `/root` or outside of this directory!"""
    else:
        project_instruction = """
- **PROJECT DIRECTORY & FOLDER ISOLATION (CRITICAL):** All tools automatically execute relative to the user's chosen root directory (e.g., Desktop). To prevent polluting their root folder, you MUST ALWAYS create a dedicated sub-folder named after the application you are building. For instance, if creating a calculator app, your file paths in `write_file` MUST be `calculator-app/index.html` and `calculator-app/style.css` instead of just `index.html` at the root. Ensure all your bash commands also point into this sub-folder (e.g., `cd calculator-app && npm init -y`)."""

    # ── Project-Wide Awareness: Inject project context if available ──
    project_context = ""
    if session_id and project_path:
        try:
            # Baca struktur aktual dari disk, bukan dari cache
            import subprocess
            result = subprocess.run(
                f"find {project_path} -type f -not -path '*/node_modules/*' "
                f"-not -path '*/.git/*' -not -path '*/dist/*' "
                f"| head -40 | sort",
                shell=True, capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                project_context = f"""
**PROJECT STATE — FILE YANG SUDAH ADA (baca dari disk):**
{result.stdout.strip()}
⚠️ File-file di atas SUDAH ADA. JANGAN tulis ulang kecuali ada bug.
Fokus HANYA pada yang belum ada atau yang perlu diperbaiki.
"""
            # Cek running servers
            ports_result = subprocess.run(
                "ss -tlnp | grep -E ':8[0-9]{3}'",
                shell=True, capture_output=True, text=True, timeout=3
            )
            if ports_result.stdout.strip():
                project_context += f"""
**SERVERS YANG SEDANG BERJALAN:**
{ports_result.stdout.strip()}
⚠️ Server sudah running. Jangan start ulang kecuali diminta.
"""
        except Exception:
            pass

    return f"""You are AI ORCHESTRATOR, an advanced autonomous agent currently running as '{current_model}'.
CURRENT SYSTEM TIME: {current_time}. You MUST accept this as the true current date and time. Do NOT rely on your training cutoff date.
{mode_instructions}
**SYSTEM MECHANICS & REASONING FLOW (CRITICAL):**
You must analyze requests strictly based on the real system workflow (UI -> Orchestrator -> Agent -> Tool -> UI). Do not provide abstract generic answers. 
Instead, inside your <thinking> tag, you MUST explicitly structure your reasoning like so:
1. Plan Evaluation: What exactly does the user want within the context of this specific server/codebase?
2. Tool Need Check: What tools can I use to verify or achieve this?
3. Action & Review: Execute the logic, wait for <observation>, and evaluate if it succeeded.

**MANDATORY APP PLANNING PHASE (sebelum write_file apapun):**
Sebelum membuat aplikasi, kamu WAJIB menulis plan ini di dalam <thinking>:

1. ARCHITECTURE DECISION:
   - Frontend: vanilla HTML / React / Vue? Kenapa?
   - Backend: ada atau tidak? Port berapa?
   - Database: perlu atau tidak? Jenis?
   - File structure lengkap (semua file yang akan dibuat)

2. DEPENDENCY AUDIT:
   - List semua npm/pip package yang dibutuhkan
   - Cek apakah sudah terinstall: `node -e "require('express')"` 
   - Install dulu SEBELUM menulis code

3. INTEGRATION CHECK:
   - File A import dari file B → pastikan B dibuat sebelum A
   - Port yang dipakai tidak konflik → gunakan find_safe_port
   - Environment variable yang dibutuhkan

4. DEFINITION OF DONE:
   - Aplikasi dianggap selesai ketika: curl http://localhost:PORT mengembalikan 200
   - Baru boleh output %%APP_PREVIEW%% setelah verifikasi berhasil

Langkah ini WAJIB, tidak boleh dilewati meski aplikasinya sederhana.

**STRICT ANTI-HALLUCINATION & TOOL USAGE RULES (MANDATORY):**
- NEVER guess or hallucinate server metrics, file contents, or system status. If asked about the system (e.g., RAM, CPU, disk, network, services), you MUST ALWAYS use the `execute_bash` tool to fetch real-time data BEFORE answering. Real-time data is your main reference.
- ALWAYS answer questions about server status. DO NOT say "I cannot process this" or "I don't have access". Always find a way using the provided tools.
- **ABSOLUTE BAN:** NEVER say "Saya tidak memiliki akses ke terminal", "I don't have access to the terminal", "saya tidak bisa melihat proses", or ANY variation claiming you lack tool access. You ALWAYS have access to `execute_bash`, `read_file`, `write_file`, and other tools. USE THEM.
- If data is not immediately available, provide an estimation based on what you can gather and explicitly explain the steps/commands to get the full data.
- Always end your server status response with a useful insight or recommendation.
- **FORMATTING REQUIREMENT:** Your final answer regarding server status must be formatted with clear labels, firm values, and colored status indicators (e.g., 🟢 OK, 🟡 WARN, 🔴 ERROR).
- ALWAYS USE TOOLS for data management and creation. If requested to create a document, manage files, or handle complex data structures (like a system table), DO NOT merely simulate the output in text. You MUST use `write_file` or `execute_bash` to actually materialize that data on the system.

**FOLLOW-UP & RESULT CHECK (CRITICAL):**
When the user asks follow-up questions like "bagaimana hasilnya?", "apakah sudah selesai?", "sudah jadi?", "cek hasilnya", or similar:
1. DO NOT answer from memory or guess. USE `execute_bash` to check the actual state (e.g., `ps aux | grep`, `curl localhost:PORT`, `ls -la project_dir/`).
2. If a server was started, verify it's still running and accessible.
3. If files were created, verify they exist and show their content if relevant.
4. Give concrete, verified answers based on real tool output.{project_instruction}

**PORT SAFETY (CRITICAL — NEVER VIOLATE):**
- The AI Orchestrator runs on port 7860. Reserved ports: 7860, 6379 (Redis), 5432 (Postgres), 3306 (MySQL), 11434 (Ollama).
- When creating any application that runs a server, you MUST use port 8100-8999. NEVER use port 7860.
- Use `find_safe_port` tool BEFORE starting any server to get a guaranteed safe port.
- The system will automatically block and reassign any command that tries to bind to a reserved port.

**INTERNET & REAL-TIME DATA (MANDATORY):**
You have FULL and UNRESTRICTED live internet access via the `web_search` tool. 
1. If a user asks for real-time information (e.g., WEATHER, news, current events, prices) or if your training data is lacking, you MUST proactively use the `web_search` tool. 
2. NEVER apologize or claim you don't have internet access or cannot provide current information. YOU DO HAVE INTERNET.
3. STRICT ANTI-HALLUCINATION: Do NOT guess, fabricate, or provide unvalidated information. All facts must be verified.
4. CITATION REQUIREMENT: When providing information obtained from the internet, you MUST explicitly cite your sources (e.g., "Berdasarkan sumber dari [Nama Situs](URL)...").
**TASK COMPLETION MANDATE:**
When asked to create applications, systems, or any complex task:
1. Create ALL necessary files and components using `write_file` or `write_multiple_files`.
2. Implement testing procedures.
3. If it is a web application (e.g. Streamlit, React, Node.js, Python Flask/FastAPI, etc.), you MUST find a safe port using `find_safe_port` and then IMMEDIATELY START THE SERVER in the background using `execute_bash` (e.g. `nohup streamlit run app.py --server.port 8100 > app.log 2>&1 &`). Do NOT just tell the user to run it; YOU MUST RUN IT.
4. Verify functionality and fix any issues found during testing.
5. Provide a working example or demo.

**APP VERIFICATION (WAJIB sebelum %%APP_PREVIEW%%):**
Setelah start server, WAJIB verifikasi dalam urutan ini:
```bash
# 1. Tunggu server ready
sleep 3

# 2. Cek process masih hidup
ps aux | grep -E "node|python|streamlit" | grep -v grep

# 3. Cek port terbuka
ss -tlnp | grep PORT

# 4. Test HTTP response
curl -s -o /dev/null -w "%{{http_code}}" http://localhost:PORT

# 5. Cek log untuk error
tail -20 app.log
```
Jika step 4 mengembalikan selain 200/301/302 → JANGAN output APP_PREVIEW.
Diagnosa error dari log, perbaiki, lalu start ulang.
Baru output APP_PREVIEW setelah curl berhasil.

6. **APP PREVIEW (CRITICAL):** If you started a background server for a web application, you MUST include the following marker at the end of your `<response>` block so the user can preview it in the UI:
%%APP_PREVIEW%%
http://localhost:<PORT>
%%END_PREVIEW%%
(Replace <PORT> with the actual safe port you used).

DO NOT stop after initial creation - continue through testing and validation until successful completion.

**NON-INTERACTIVE PACKAGE INSTALL (WAJIB):**
Semua perintah instalasi HARUS menggunakan flag non-interactive:
- npm: `npm install --yes --no-audit --no-fund`
- pip: `pip install -q --no-input`
- apt: `DEBIAN_FRONTEND=noninteractive apt-get install -y`
- yarn: `yarn install --non-interactive`
JANGAN pernah jalankan perintah yang menunggu input user.

**FILE CACHE RULE (hemat token):**
Dalam satu sesi task, jika kamu sudah membaca sebuah file:
- Catat isinya di <thinking> dengan label [CACHED: filename]
- JANGAN baca ulang file yang sama di iterasi berikutnya
- Hanya baca ulang jika kamu BARU SAJA menulis perubahan ke file itu

Urutan yang BENAR untuk modifikasi file:
1. read_file (sekali saja)
2. Analisis di <thinking>  
3. write_file dengan konten yang sudah dimodifikasi
4. Verifikasi dengan execute_bash (bukan read_file lagi)

**SMART RESUME RULE (CRITICAL — prevents wasted tokens):**
When the user says ANY of these intent keywords:
- CONTINUE intents: "lanjutkan", "continue", "teruskan", "next"  
- RUN intents: "jalankan", "run", "start", "eksekusi", "execute"
- TEST intents: "deploy", "test", "coba", "preview", "buka"

You MUST follow this workflow:
1. FIRST run `execute_bash` with `ls -la <project_dir>` to see what files already exist.
2. THEN read key existing files (index.html, main.py, package.json, etc.) to understand the current state.
3. If project already has files:
   - For RUN/TEST intents: Jump DIRECTLY to running/testing. DO NOT re-create files.
   - For CONTINUE intents: Only create MISSING files. Never re-create existing ones.
4. If starting a server, check if it's already running: `ps aux | grep <app_name>`
5. NEVER rebuild a project from scratch if files already exist.

Violating this rule wastes tokens and frustrates the user.

**ABSOLUTE RULE — OUTPUT FORMAT:**
You MUST wrap your entire output in EXACTLY these XML tags. NO EXCEPTIONS.
DO NOT write any conversational text, greetings, or explanations before the `<thinking>` or `<think>` tag. Your response MUST start exactly with `<thinking>` or `<think>`.

Step 1 (HIDDEN from user): Put ALL your reasoning, analysis, and tool calls inside:
<thinking>
...your internal analysis, tool calls, etc...
</thinking>

Step 2 (SHOWN to user): Put ONLY your final answer inside:
<response>
...direct answer to user, formatted in Markdown...
</response>

CRITICAL: Do NOT write ANY text outside of these two tags. The system will BLOCK everything that is not inside `<response>` tags. If you write text without tags, it breaks the system.

**THINKING QUALITY — WAJIB STRUCTURED SEPERTI ENGINEER SENIOR:**
Di dalam <thinking>, tulis reasoning dengan sub-judul yang jelas. 
Contoh yang BENAR (seperti yang diharapkan user):

<thinking>
## Memahami Permintaan
User ingin membuat todo app dengan fitur login. Perlu auth + CRUD.

## Keputusan Arsitektur
- Frontend: React via CDN (tidak perlu build step, deploy lebih cepat)
- Backend: Express.js (ringan, familiar, banyak contoh)
- Database: SQLite dengan better-sqlite3 (zero config, cocok untuk single-user)
- Auth: JWT + bcrypt (standar industri)

## File Structure
todo-app/
├── server.js        # Express backend
├── package.json     # dependencies
└── public/
├── index.html   # React SPA
└── app.js       # React components

## Dependency Check
Perlu install: express, better-sqlite3, bcryptjs, jsonwebtoken, cors
Command: npm install --yes --no-audit --no-fund express better-sqlite3 bcryptjs jsonwebtoken cors

## Potensi Masalah
1. CORS: frontend (file://) vs backend (localhost:PORT) → konfigurasi cors() dengan origin: '*'
2. JWT_SECRET: harus random dan disimpan di env
3. SQLite path: gunakan path.join(__dirname, 'db.sqlite') bukan relative path

## Urutan Eksekusi
1. find_safe_port → dapat port bebas
2. write_multiple_files → scaffold semua file sekaligus
3. execute_bash: cd todo-app && npm install --yes --no-audit
4. execute_bash: nohup node server.js > app.log 2>&1 & sleep 3
5. execute_bash: curl -s localhost:PORT → verifikasi 200 OK
6. Output %%APP_PREVIEW%%

## Estimasi: ~3 menit
</thinking>

JANGAN tulis thinking yang pendek atau generik seperti:
"User wants an app. I'll create it now."
Semakin detail thinking = semakin sedikit error = semakin sedikit retry = hemat token.

**FILE SAVING CAPABILITY:**
When the user asks you to save results to a directory/folder/file, DO NOT refuse. Include the following special marker at the END of your `<response>` block:
%%SAVE_FILE%%
filename: nama-file-yang-relevan.txt
content:
[isi lengkap yang akan disimpan]
%%END_SAVE%%

The system will automatically detect this marker and show a "Save File" dialog to the user in their browser, where they can choose the destination folder.
RULES:
- Always include the %%SAVE_FILE%% marker if the user requests saving or exporting content.
- Choose a descriptive filename based on context (e.g., server-report.txt, analysis.log, data-export.csv).
- The content inside the marker must be complete and ready to be saved.
- NEVER say "I cannot save to a directory" or "I don't have access to your file system".

Available tools (use INSIDE <thinking> only):
1. execute_bash — run a command. Args: command (string). NOTE: port collision protection is built-in.
2. read_file — read a file. Args: path (string).
3. write_file — write a file. Args: path (string), content (string).
4. write_multiple_files — write multiple files at once. Use this to scaffold applications. Args: files_data (list of objects with 'path' and 'content' keys). Example: [{{"path": "file.py", "content": "code"}}]
5. ask_model — ask another AI for data processing. Args: model_id (string), prompt (string). Models: {model_list_str}.
6. web_search — search the web. Args: query (string).
7. find_safe_port — find a free port that won't conflict with AI Orchestrator. Args: preferred (int, optional). ALWAYS call this before starting any server.

Tool format (inside <thinking>):
<tool>{{"name": "tool_name", "args": {{"key": "value"}}}}</tool>
Stop generating immediately after a <tool> block. You will get results in <observation>.

Example for a simple greeting:
<thinking>
Simple greeting, no tools needed.
</thinking>
<response>
Hai! 👋 Ada yang bisa saya bantu?
</response>

Example for a system check:
<thinking>
1. Plan Evaluation: User wants RAM info.
2. Tool Need Check: I need to run a command.
3. Action & Review: Executing bash.
<tool>{{"name": "execute_bash", "args": {{"command": "free -h"}}}}</tool>
</thinking>
[receives observation]
<response>
**RAM Server:**
- Total: 4 GB
- Used: 1.8 GB (45%)
- Free: 2.2 GB
</response>

Example for asking another model:
<thinking>
1. Plan Evaluation: User wants a poem.
2. Tool Need Check: I will delegate to another model.
3. Action & Review: Let's ask deepseek.
<tool>{{"name": "ask_model", "args": {{"model_id": "deepseek-v3-2", "prompt": "Write a poem"}}}}</tool>
</thinking>
[receives observation]
<response>
Here is the poem written by the other model...
</response>

**PROJECT-WIDE AWARENESS:**
When modifying files in a project, you MUST consider the impact on other files.
If you change File A and File B depends on it, you MUST also update File B.
Always think about import/dependency relationships between files.
{project_context}

**STANDAR KUALITAS APLIKASI (wajib dipenuhi sebelum selesai):**

✅ FRONTEND:
- Responsive (mobile + desktop)
- Loading state saat fetch data
- Error handling — tampilkan pesan jika API gagal
- Input validation sebelum submit
- UI yang bersih, tidak berantakan

✅ BACKEND:
- Semua endpoint return JSON yang konsisten
- Error response dengan status code yang tepat (400, 404, 500)
- CORS dikonfigurasi jika frontend dan backend beda port
- Environment variable untuk config sensitif

✅ INTEGRASI:
- Frontend bisa konek ke backend (tidak ada CORS error)  
- Data flow end-to-end berfungsi
- Tidak ada console.error atau Python traceback saat normal use

✅ DEPLOYMENT CHECK:
- `curl http://localhost:PORT` → 200 OK
- `curl http://localhost:PORT/api/health` → {{"status": "ok"}}
- Server berjalan di background dengan PID tercatat

Jika ada yang belum terpenuhi, JANGAN bilang selesai. Perbaiki dulu.
"""


class ResponseFilter:
    """
    TagRewriter/Filter.
    Wraps <thinking> or <think> blocks into <details> dropdowns.
    Only emits content from <response> naturally or inside the <details> wrapper.
    If the model fails to use tags, falls back to emitting raw text.
    """
    def __init__(self, emit_thinking: bool = True):
        self.state = "WAITING"
        self.pending = ""
        self.ever_emitted_response = False
        self.emit_thinking = emit_thinking
        self.current_think_tag = "</thinking>"
        # ── Thinking capture ──────────────────────────────────
        self._thinking_buffer = ""   # accumulate thinking chunks
        self._thinking_ready = ""    # complete thinking block, siap diambil executor

    def process(self, chunk: str) -> str:
        self.pending += chunk
        output = ""

        # Auto-fallback: if we haven't seen any known tags within the first 100 chars,
        # we assume the model failed to follow instructions and just emit raw text.
        if self.state == "WAITING" and len(self.pending) > 100:
            if not any(t in self.pending for t in ["<think", "<response>", "<tool>"]):
                self.state = "RAW"
                
        if self.state == "RAW":
            self.ever_emitted_response = True
            out = self.pending
            self.pending = ""
            return out

        while self.pending and self.state != "RAW":
            if self.state == "WAITING":
                i_think1 = self.pending.find("<thinking>")
                i_think2 = self.pending.find("<think>")
                
                i_think = -1
                think_len = 0
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

                i_resp = self.pending.find("<response>")
                i_tool = self.pending.find("<tool>")

                tags = []
                if i_think != -1: tags.append((i_think, think_len, "thinking"))
                if i_resp != -1: tags.append((i_resp, len("<response>"), "response"))
                if i_tool != -1: tags.append((i_tool, len("<tool>"), "tool"))

                if tags:
                    tags.sort(key=lambda x: x[0])
                    idx, tag_len, tag_type = tags[0]
                    # Check if there is plain text before the first tag. If it's substantial, emit it.
                    if idx > 15 and not self.ever_emitted_response:
                        output += self.pending[:idx]
                        self.ever_emitted_response = True
                        
                    self.pending = self.pending[idx:]
                    if tag_type == "thinking":
                        # NEVER emit thinking as raw text — capture silently and send as process event
                        self._thinking_buffer = ""  # reset buffer untuk thinking baru
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
                idx_tool = self.pending.find("<tool>")
                
                if idx_tool != -1 and (end_think == -1 or idx_tool < end_think):
                    # Tool ditemukan sebelum thinking selesai — simpan yang sudah ada
                    partial = self.pending[:idx_tool]
                    self._thinking_buffer += partial
                    # Simpan sebagai thinking_ready meski belum selesai
                    if self._thinking_buffer.strip():
                        self._thinking_ready = self._thinking_buffer.strip()
                    if self.emit_thinking:
                        output += partial
                    self.pending = self.pending[idx_tool:]
                    break
                
                if end_think != -1:
                    # Thinking selesai — capture seluruh konten (SILENT, never emit as text)
                    thinking_text = self.pending[:end_think]
                    self._thinking_buffer += thinking_text
                    # Simpan ke _thinking_ready agar bisa diambil executor
                    self._thinking_ready = self._thinking_buffer.strip()
                    self._thinking_buffer = ""
                    # TIDAK emit thinking ke output — hanya capture
                    self.pending = self.pending[end_think + len(self.current_think_tag):]
                    self.state = "WAITING"
                else:
                    safe = len(self.pending) - 15
                    if safe > 0:
                        chunk_part = self.pending[:safe]
                        self._thinking_buffer += chunk_part  # accumulate (SILENT)
                        # TIDAK emit ke output
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
            # Flush sisa thinking — capture silently
            self._thinking_buffer += self.pending
            self._thinking_ready = self._thinking_buffer.strip()
            self._thinking_buffer = ""
            self.pending = ""
            return ""  # Never emit thinking as raw text
        elif self.state == "RESPONSE" and self.pending:
            res = self.pending
            self.pending = ""
            return res
        elif self.state == "RAW" and self.pending:
            res = self.pending
            self.pending = ""
            return res
        return ""

    def pop_thinking(self) -> str:
        """Ambil thinking content yang sudah ter-capture, lalu reset."""
        result = self._thinking_ready
        self._thinking_ready = ""
        return result


class AgentExecutor:
    def _prune_agent_messages(self, messages: list) -> list:
        """Remove <thinking> blocks and enforce token/message limits."""
        for msg in messages:
            if msg["role"] == "assistant":
                msg["content"] = re.sub(r'<thinking>.*?</thinking>', '', msg["content"], flags=re.DOTALL)
                msg["content"] = re.sub(r'<think>.*?</think>', '', msg["content"], flags=re.DOTALL)
        
        if len(messages) > 20:
            return messages[:2] + messages[-10:]
        return messages

    def _safe_parse_tool_json(self, text: str) -> dict:
        """Robust JSON parsing with 4 fallback strategies."""
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # Strategy 1: Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract outermost JSON object using balanced brace matching
        # This handles escaped quotes, nested objects, etc.
        start_idx = text.find('{')
        if start_idx != -1:
            depth = 0
            in_string = False
            escape_next = False
            end_idx = -1
            for i in range(start_idx, len(text)):
                c = text[i]
                if escape_next:
                    escape_next = False
                    continue
                if c == '\\':
                    escape_next = True
                    continue
                if c == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end_idx = i
                        break
            if end_idx != -1:
                candidate = text[start_idx:end_idx + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass
            
        # Strategy 3: Simple regex extraction (greedy)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
                
        # Strategy 4: Fix common formatting issues (single quotes, trailing commas)
        try:
            fixed_text = text.replace("'", '"')
            fixed_text = re.sub(r',\s*\}', '}', fixed_text)
            fixed_text = re.sub(r',\s*\]', ']', fixed_text)
            return json.loads(fixed_text)
        except Exception:
            pass
            
        return None

    async def stream_chat(
        self,
        base_model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        include_tool_logs: bool = True,
        emit_thinking: bool = True,
        execution_mode: str = "execution",
        session_id: str = None,
        project_path: str = None,
    ) -> AsyncGenerator[str, None]:
        
        system_prompt = build_agent_system_prompt(base_model, execution_mode, project_path, session_id)
        
        # Inject our agent system prompt
        agent_msgs = list(messages)
        has_system = False
        for m in agent_msgs:
            if m["role"] == "system":
                m["content"] += f"\n\n{system_prompt}"
                has_system = True
                break
        if not has_system:
            agent_msgs.insert(0, {"role": "system", "content": system_prompt})
            
        MAX_ITERATIONS = 30
        response_filter = ResponseFilter(emit_thinking=emit_thinking)
        consecutive_errors = 0  # Track consecutive errors for circuit breaker
        
        for iteration in range(MAX_ITERATIONS):
            # ── Circuit breaker: stop if too many consecutive errors ──
            if consecutive_errors >= 3:
                yield "\n\n⚠️ Terlalu banyak error beruntun. Proses dihentikan untuk mencegah loop. Silakan ulangi pertanyaan Anda.\n"
                break
            
            buffer = ""
            has_tool_started = False
            stream_error = False
            
            # ══════════════════════════════════════════════════════════
            # ERROR RESILIENCE: Wrap the ENTIRE model stream in try/except
            # so a mid-stream API failure never crashes the process.
            # ══════════════════════════════════════════════════════════
            try:
                async for chunk in model_manager.chat_stream(base_model, agent_msgs, temperature, max_tokens):
                    buffer += chunk
                    
                    if not has_tool_started:
                        filtered = response_filter.process(chunk)
                        if filtered:
                            yield filtered
                    
                    if "<tool>" in buffer and not has_tool_started:
                        has_tool_started = True
                        
                        # Flush any remaining text before transitioning to tool mode to prevent cutoff
                        flushed = response_filter.flush()
                        if flushed:
                            yield flushed
                            
                        # Reset filter gracefully so next iteration starts fresh
                        response_filter.state = "WAITING"
                        response_filter.pending = ""
                    
                    if has_tool_started:
                        if "</tool>" in buffer:
                            break
                            
            except asyncio.CancelledError:
                # Client disconnected — stop gracefully, don't retry
                log.info("Stream cancelled by client")
                return
            except Exception as stream_err:
                stream_error = True
                consecutive_errors += 1
                err_msg = str(stream_err)[:200]
                log.warning("Model stream error, recovering", error=err_msg, iteration=iteration)

                # Specific: Sumopod "model output empty" error → retry with simplified message
                is_empty_output_err = (
                    "model output must contain" in err_msg.lower() or
                    "output text or tool calls" in err_msg.lower() or
                    "cannot both be empty" in err_msg.lower()
                )

                if is_empty_output_err and consecutive_errors <= 2:
                    log.warning("Sumopod empty output error, simplifying prompt and retrying")
                    # Simplify prompt TAPI tetap pertahankan tool instructions agar AI tidak
                    # kehilangan kemampuan execute_bash, read_file, dll.
                    last_user = next(
                        (m["content"] for m in reversed(agent_msgs) if m["role"] == "user"),
                        "Tolong jawab pertanyaan saya"
                    )
                    # Rebuild with minimal but tool-capable system prompt
                    minimal_system = build_agent_system_prompt(base_model, execution_mode, project_path, session_id)
                    agent_msgs = [
                        {"role": "system", "content": minimal_system},
                        {"role": "user", "content": last_user[:2000]},
                    ]
                    await asyncio.sleep(1.0)
                    continue

                if include_tool_logs:
                    yield f"\n> ⚠️ **Stream error (auto-recovering):** {err_msg[:100]}\n"

                # If we got partial buffer with content, try to use it. Otherwise retry.
                if not buffer.strip():
                    # Inject the error as observation so the model can adapt
                    agent_msgs.append({"role": "assistant", "content": "<thinking>Stream error occurred.</thinking>"})
                    agent_msgs.append({"role": "user", "content": f"<observation>\nStream error: {err_msg}. Please continue from where you left off.\n</observation>"})
                    agent_msgs = self._prune_agent_messages(agent_msgs)
                    await asyncio.sleep(min(2 ** consecutive_errors, 8))  # Exponential backoff
                    continue
            
            # ── EMIT THINKING sebagai process sentinel ──────────────
            # Ambil thinking content yang sudah di-capture ResponseFilter
            captured_thinking = response_filter.pop_thinking()
            if captured_thinking and len(captured_thinking) > 30:
                word_count = len(captured_thinking.split())
                yield process_emitter.to_sentinel(
                    "Thinking",
                    f"Reasoning ({word_count} kata)",
                    extra={"result": captured_thinking}
                )
            
            # Check if model intends to use a tool
            has_tool = "<tool>" in buffer
            if has_tool and "</tool>" not in buffer:
                buffer += "</tool>"
                
            if has_tool:
                # Reset consecutive error counter on successful tool parse
                try:
                    tool_content = buffer.split("<tool>")[1].split("</tool>")[0].strip()
                    
                    # Clean markdown code blocks
                    clean_content = tool_content
                    if clean_content.startswith("```json"):
                        clean_content = clean_content[7:]
                    elif clean_content.startswith("```"):
                        clean_content = clean_content[3:]
                    if clean_content.endswith("```"):
                        clean_content = clean_content[:-3]
                    
                    clean_content = clean_content.strip()
                    
                    # Robust parsing with 4 fallback strategies
                    tool_req = self._safe_parse_tool_json(clean_content)
                    if tool_req is None:
                        raise Exception(f"Failed to parse tool JSON. Raw text: {clean_content[:100]}...")
                    
                    cmd = tool_req.get("name")
                    args = tool_req.get("args", {})
                    
                    consecutive_errors = 0  # Reset on successful parse

                    # ── Map cmd → structured process action ──────────
                    _TOOL_ACTION_MAP = {
                        "execute_bash":        ("Ran",      lambda a: a.get("command", "")[:60]),
                        "read_file":           ("Reading",  lambda a: a.get("path", "").split("/")[-1]),
                        "write_file":          ("Writing",  lambda a: a.get("path", "").split("/")[-1]),
                        "write_multiple_files":("Writing",  lambda a: f"{len(a.get('files_data', []))} files"),
                        "ask_model":           ("Analyzed", lambda a: a.get("model_id", "")),
                        "web_search":          ("Searched", lambda a: a.get("query", "")[:60]),
                        "find_safe_port":      ("Checked",  lambda a: "available port"),
                    }
                    _action, _detail_fn = _TOOL_ACTION_MAP.get(
                        cmd, ("Worked", lambda a: cmd)
                    )
                    _detail = _detail_fn(args)

                    # Emit structured process event BEFORE executing (via sentinel)
                    yield process_emitter.to_sentinel(_action, _detail)

                    # Execute tool — each tool execution is individually wrapped
                    res = ""
                    try:
                        async def _exec_tool():
                            if execution_mode == "analysis" and cmd in ["execute_bash", "write_file", "write_multiple_files"]:
                                return f"Operation simulated (Analysis Mode Active). Tool {cmd} skipped to guarantee safety."
                            
                            from agents.tools import write_multiple_files, find_safe_port
                            
                            if cmd == "execute_bash":
                                return await execute_bash(args.get("command", ""), session_id)
                            elif cmd == "read_file":
                                return await read_file(args.get("path", ""), session_id)
                            elif cmd == "write_file":
                                return await write_file(args.get("path", ""), args.get("content", ""), session_id)
                            elif cmd == "write_multiple_files":
                                return await write_multiple_files(args.get("files_data", []), session_id)
                            elif cmd == "ask_model":
                                return await ask_model(args.get("model_id", ""), args.get("prompt", ""))
                            elif cmd == "web_search":
                                return await web_search(args.get("query", ""))
                            elif cmd == "find_safe_port":
                                return await find_safe_port(args.get("preferred", 0))
                            else:
                                return f"Unknown tool: {cmd}. Available tools: execute_bash, read_file, write_file, write_multiple_files, ask_model, web_search, find_safe_port"
                        # Fix 2: Heartbeat pattern — kirim status setiap 20 detik, max 10 menit
                        HEARTBEAT_INTERVAL = 20.0
                        MAX_TOOL_TIME = 600.0  # 10 menit cukup untuk npm install

                        tool_task = asyncio.create_task(_exec_tool())
                        elapsed = 0.0
                        res = None

                        while not tool_task.done():
                            try:
                                res = await asyncio.wait_for(
                                    asyncio.shield(tool_task),
                                    timeout=HEARTBEAT_INTERVAL
                                )
                                break  # selesai normal
                            except asyncio.TimeoutError:
                                elapsed += HEARTBEAT_INTERVAL
                                if elapsed >= MAX_TOOL_TIME:
                                    tool_task.cancel()
                                    try:
                                        await tool_task
                                    except asyncio.CancelledError:
                                        pass
                                    res = f"Tool {cmd} timeout setelah {int(MAX_TOOL_TIME/60)} menit."
                                    yield process_emitter.to_sentinel("Error", f"{cmd} timeout {int(MAX_TOOL_TIME/60)}m")
                                    break
                                # Kirim heartbeat → frontend tahu masih hidup
                                yield process_emitter.to_sentinel(
                                    "Ran",
                                    f"{_detail[:40]} ({int(elapsed)}s)...",
                                )

                        if res is None:
                            res = f"Tool {cmd} tidak menghasilkan output."
                    except Exception as e:
                        res = f"Error executing tool {cmd}: {str(e)}. The tool encountered an error but the process continues."
                        yield process_emitter.to_sentinel("Error", str(e)[:80])
                    
                    # After successful write_file: emit file content so frontend can show artifact
                    if cmd == "write_file" and not res.startswith("Error") and not res.startswith("Tool "):
                        file_path    = args.get("path", "")
                        file_content = args.get("content", "")
                        if file_path and file_content:
                            ext  = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "txt"
                            # Emit Written sentinel carrying file content (cap at 8000 chars)
                            yield process_emitter.to_sentinel(
                                "Written", file_path,
                                extra={"code": file_content[:8000], "language": ext, "truncated": len(file_content) > 8000}
                            )

                    # After write_multiple_files: emit last file so artifact panel updates
                    elif cmd == "write_multiple_files" and not res.startswith("Error") and not res.startswith("Tool "):
                        files_data = args.get("files_data", [])
                        if files_data:
                            last_file = files_data[-1]
                            fp = last_file.get("path", "")
                            fc = last_file.get("content", "")
                            if fp and fc:
                                ext = fp.rsplit(".", 1)[-1].lower() if "." in fp else "txt"
                                yield process_emitter.to_sentinel(
                                    "Written", fp,
                                    extra={"code": fc[:8000], "language": ext, "truncated": len(fc) > 8000}
                                )

                    # Emit a 'Found' step if result has useful content (non-write tools)
                    if cmd not in ("write_file", "write_multiple_files") and include_tool_logs and res and not res.startswith("Error") and not res.startswith("Tool "):
                        lines = res.strip().splitlines()
                        n = len(lines)
                        if n > 1:
                            yield process_emitter.to_sentinel("Found", f"{n} lines", count=n)
                            
                    # Klasifikasi error untuk bantu model analisis
                    error_hint = ""
                    if "ENOENT" in str(res) or "No such file" in str(res):
                        error_hint = "\n[HINT: File/direktori tidak ditemukan. Cek path dan buat direktori dulu dengan mkdir -p]"
                    elif "EADDRINUSE" in str(res) or "address already in use" in str(res):
                        error_hint = "\n[HINT: Port sudah dipakai. Gunakan find_safe_port atau kill proses lama]"
                    elif "MODULE_NOT_FOUND" in str(res) or "ModuleNotFoundError" in str(res):
                        error_hint = "\n[HINT: Package belum terinstall. Jalankan npm install atau pip install dulu]"
                    elif "SyntaxError" in str(res) or "IndentationError" in str(res):
                        error_hint = "\n[HINT: Ada syntax error di kode. Baca file yang bermasalah lalu perbaiki]"
                    elif "Permission denied" in str(res):
                        error_hint = "\n[HINT: Permission error. Cek dengan ls -la dan gunakan chmod atau sudo jika perlu]"
                    elif "connection refused" in str(res).lower():
                        error_hint = "\n[HINT: Server belum ready atau crash. Cek log dengan tail -30 app.log]"

                    # Kirim hasil tool ke frontend agar bisa ditampilkan di step toggle
                    if cmd == "execute_bash" and res and not res.startswith("Error"):
                        # Batasi output bash ke 2000 char agar tidak membanjiri
                        display_res = res[:2000] + ("\n...[output dipotong]" if len(res) > 2000 else "")
                        yield process_emitter.to_sentinel(
                            "Found",
                            f"output: {args.get('command','')[:40]}",
                            extra={"result": display_res}
                        )
                    elif cmd == "read_file" and res and not res.startswith("Error"):
                        display_res = res[:3000] + ("\n...[dipotong]" if len(res) > 3000 else "")
                        yield process_emitter.to_sentinel(
                            "Reading",  
                            args.get("path", "").split("/")[-1],
                            extra={"result": display_res}
                        )
                    elif cmd == "web_search" and res and not res.startswith("Error"):
                        yield process_emitter.to_sentinel(
                            "Fetched",
                            args.get("query","")[:50],
                            extra={"result": res[:2000]}
                        )

                    obs_text = f"\n<observation>\n{res}{error_hint}\n</observation>\n"
                    
                    # Only store the tool call in history, without the pre-tool thinking text
                    agent_msgs.append({"role": "assistant", "content": f"<tool>{tool_content}</tool>"})
                    agent_msgs.append({"role": "user", "content": obs_text})
                    agent_msgs = self._prune_agent_messages(agent_msgs)
                    
                except Exception as e:
                    consecutive_errors += 1
                    if include_tool_logs:
                        yield f"\n> ⚠️ **Tool parse error (recovering):** {str(e)[:100]}\n"
                    err_obs = f"\n<observation>\nError parsing or executing tool: {str(e)}. Please fix the JSON format and try again.\n</observation>\n"
                    agent_msgs.append({"role": "assistant", "content": buffer})
                    agent_msgs.append({"role": "user", "content": err_obs})
                    agent_msgs = self._prune_agent_messages(agent_msgs)
            else:
                # No tool call => stream ended
                # Flush any remaining content in the filter
                remaining = response_filter.flush()
                if remaining:
                    yield remaining
                
                # SAFE FALLBACK: If the model never used <response> tags,
                # salvage the raw text.
                if not response_filter.ever_emitted_response:
                    # Explicitly remove the entire <thinking> or <think> block and its contents first
                    fallback_text = re.sub(r'<(?:thinking|think)>.*?</(?:thinking|think)>', '', buffer, flags=re.DOTALL)
                    # Remove any loose tags remaining
                    fallback_text = re.sub(r'</?(?:thinking|think|response|tool|observation)>', '', fallback_text).strip()
                    if fallback_text:
                        # ── Self-Correction Loop: review code before yielding ──
                        try:
                            from core.self_correction import self_correction_engine
                            corrected, report = await self_correction_engine.review_and_correct(
                                fallback_text, base_model, agent_msgs[0].get("content", "")[:300] if agent_msgs else ""
                            )
                            if report.total_issues_fixed > 0:
                                log.info("Self-correction applied",
                                         fixed=report.total_issues_fixed,
                                         found=report.total_issues_found)
                                yield corrected
                                yield f"\n\n✅ *Self-Correction: {report.total_issues_fixed} error otomatis diperbaiki.*"
                            else:
                                yield fallback_text
                        except Exception as sc_err:
                            log.debug("Self-correction skipped", error=str(sc_err)[:80])
                            yield fallback_text
                    elif not stream_error:
                        yield "⚠️ Proses selesai namun tidak ada respons yang dihasilkan. Silakan ulangi pertanyaan Anda."
                
                break

agent_executor = AgentExecutor()


