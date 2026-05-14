"""
AI Orchestrator — Plan Generator (v1.0)
=======================================
Menghasilkan rencana implementasi terstruktur sebelum eksekusi dimulai
untuk task kompleks (pembuatan aplikasi, perbaikan, peningkatan fitur).

Mirip dengan cara Antigravity AI / VS Code Copilot menampilkan rencana
sebelum mengeksekusi, sehingga pengguna tahu apa yang akan dilakukan.

Output: Markdown-formatted plan dengan:
  - Ringkasan singkat apa yang akan dibuat/diperbaiki
  - Langkah-langkah eksekusi (numbered)
  - Daftar file yang akan dibuat/diubah
  - Estimasi waktu
"""

import json
import asyncio
import structlog
from typing import Optional

log = structlog.get_logger()

# Trigger keywords yang menandakan perlu ditampilkan plan
PLAN_TRIGGERS = {
    # Pembuatan baru
    "buat", "bikin", "buatkan", "create", "build", "generate", "bangun",
    "buat aplikasi", "bikin aplikasi", "buat website", "bikin website",
    "buat program", "buatkan program", "buat sistem", "buatkan sistem",
    "buat bot", "buatkan bot", "buat api", "buatkan api",
    "buat fitur", "buatkan fitur", "tambahkan fitur", "tambah fitur",
    # Perbaikan / modifikasi
    "perbaiki", "fix", "repair", "debug", "refactor", "optimize",
    "improve", "tingkatkan", "perbarui", "update", "upgrade", "migrasikan",
    "tambah", "tambahkan", "integrasikan", "konfigurasi", "setup",
    # Scope penuh
    "full", "lengkap", "complete", "end-to-end", "dari awal", "from scratch",
}

# Intent yang selalu butuh plan
PLAN_INTENTS = {"coding", "web_development", "file_operation", "system"}

PLAN_PROMPT = """Kamu adalah AI Planner. Tugas kamu adalah membuat rencana implementasi yang jelas dan terstruktur.

User meminta: {user_message}
Kategori tugas: {intent}
Konteks tambahan: {context}

Buat rencana implementasi dalam format Markdown yang ringkas tapi informatif.

ATURAN FORMAT:
- Gunakan Bahasa Indonesia
- Singkat tapi lengkap (max 15 langkah)
- Setiap langkah harus actionable dan konkret
- Sebutkan teknologi/tools yang akan digunakan
- Sebutkan file-file utama yang akan dibuat/diubah
- Jangan ada basa-basi, langsung ke poin

FORMAT OUTPUT (ikuti PERSIS):
## 📋 Rencana: {title}

**Ringkasan:** [1-2 kalimat apa yang akan dibangun/diperbaiki]

**Stack/Tools:** [teknologi utama, misal: Python, FastAPI, SQLite, HTML/CSS/JS]

**Langkah Eksekusi:**
1. [langkah konkret pertama]
2. [langkah konkret kedua]
...dst (max 10 langkah)

**File yang akan dibuat/diubah:**
- `path/file.ext` — [fungsi singkat]
...dst

**Estimasi:** [misal: ~5 menit | ~15 menit | ~30 menit]

Jawab HANYA dengan output di atas, tanpa kalimat tambahan apapun."""


def should_generate_plan(message: str, intent: str, action_type: str) -> bool:
    """Tentukan apakah request ini perlu ditampilkan plan."""
    if action_type != "execute":
        return False

    if intent not in PLAN_INTENTS:
        return False

    msg_lower = message.lower()
    return any(trigger in msg_lower for trigger in PLAN_TRIGGERS)


async def generate_plan(
    message: str,
    intent: str,
    context: str = "",
    timeout: float = 12.0,
) -> Optional[str]:
    """
    Generate implementation plan menggunakan AI.
    Return: markdown string plan, atau None jika gagal/timeout.
    """
    try:
        from core.model_manager import model_manager
        from agents.agent_registry import agent_registry

        # Pakai reasoning model untuk generate plan yang berkualitas
        model = agent_registry.resolve_model_for_agent("reasoning")
        if not model:
            model = model_manager.get_default_model()
        if not model:
            return None

        # Extract judul singkat dari pesan user
        words = message.strip().split()
        title = " ".join(words[:8]) + ("..." if len(words) > 8 else "")

        prompt = PLAN_PROMPT.format(
            user_message=message[:500],
            intent=intent,
            context=context[:300] if context else "tidak ada",
            title=title,
        )

        messages = [
            {"role": "system", "content": "Kamu adalah AI Planner. Buat rencana implementasi yang jelas dan terstruktur. Jawab HANYA dengan format yang diminta."},
            {"role": "user", "content": prompt},
        ]

        # Collect full response
        chunks = []
        async for chunk in asyncio.wait_for(
            model_manager.chat_stream(
                model=model,
                messages=messages,
                temperature=0.2,
                max_tokens=1200,
            ),
            timeout=timeout,
        ):
            if chunk:
                chunks.append(chunk)

        raw = "".join(chunks).strip()

        # Strip <thinking> blocks jika ada
        import re
        raw = re.sub(r'<(?:thinking|think)>.*?</(?:thinking|think)>', '', raw, flags=re.DOTALL).strip()
        raw = re.sub(r'</?(?:response|tool)>', '', raw).strip()

        if not raw or len(raw) < 50:
            return None

        return raw

    except asyncio.TimeoutError:
        log.warning("plan_generator: timeout generating plan")
        return None
    except Exception as e:
        log.warning("plan_generator: failed", error=str(e)[:80])
        return None


def build_quick_plan(message: str, intent: str, subtasks: list) -> str:
    """
    Fallback: buat plan sederhana dari subtasks yang sudah ada
    tanpa panggilan AI (untuk kasus timeout atau error).
    """
    lines = [f"## 📋 Rencana Eksekusi\n"]
    lines.append(f"**Permintaan:** {message[:200]}\n")
    lines.append(f"**Tipe:** {intent}\n")
    lines.append(f"\n**Langkah yang akan dieksekusi:**\n")

    for i, st in enumerate(subtasks, 1):
        desc = getattr(st, 'description', str(st))[:120]
        task_type = getattr(st, 'task_type', intent)
        agent = getattr(st, 'assigned_agent', None)
        agent_tag = f" [{agent}]" if agent else ""
        lines.append(f"{i}. **[{task_type}]{agent_tag}** {desc}")

    lines.append(f"\n_Eksekusi dimulai secara otomatis..._")
    return "\n".join(lines)
