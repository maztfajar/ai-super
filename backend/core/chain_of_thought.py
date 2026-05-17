"""
Orchestra Chain of Thought Engine — v2.0
=========================================
Mesin penalaran bertahap yang terintegrasi penuh dengan:
  - model_manager.chat_completion() (interface nyata dari model_manager.py)
  - TaskSpecification + EmotionalState (dari request_preprocessor.py v3.0)
  - OrchestratorEvent (dari orchestrator.py) untuk SSE streaming ke UI
  - QMD token distiller (jika tersedia)

Arsitektur:
  FAST    → 1 tahap  (trivial/salam)
  STANDARD → 3 tahap (pertanyaan umum)
  DEEP    → 5 tahap (coding, debugging, analisis)
  EXPERT  → 7 tahap + self-correction (multi-domain, proyek kompleks)

Cara pakai di orchestrator.py:
  from core.chain_of_thought import cot_engine, should_use_cot, CoTDepth

  # Di PHASE 1.5 — setelah preprocessor, sebelum fast-path:
  if should_use_cot(spec):
      async for event in cot_engine.stream_reason(
          spec=spec,
          history=history,
          system_prompt=system_prompt,
      ):
          if event.type == "cot_done":
              system_prompt = event.data["enriched_prompt"]
          else:
              yield event   # forward status ke UI
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator, Dict, List, Optional, Any
import structlog

log = structlog.get_logger()


# ══════════════════════════════════════════════════════════════════════════════
# DEPTH & STAGE DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

class CoTDepth(Enum):
    FAST     = "fast"      # 1 call — trivial
    STANDARD = "standard"  # 3 calls — pertanyaan umum
    DEEP     = "deep"      # 5 calls — coding / analisis
    EXPERT   = "expert"    # 7 calls — multi-domain / proyek kritis


class ThoughtStage(Enum):
    DECOMPOSE      = "decompose"       # Urai masalah
    CONTEXTUALIZE  = "contextualize"   # Baca emosi & situasi
    ANALYZE        = "analyze"         # Analisis mendalam
    SYNTHESIZE     = "synthesize"      # Susun jawaban
    VALIDATE       = "validate"        # Cek kualitas jawaban
    CORRECT        = "correct"         # Self-correction
    REFLECT        = "reflect"         # Refleksi akhir


DEPTH_STAGES: Dict[CoTDepth, List[ThoughtStage]] = {
    CoTDepth.FAST: [
        ThoughtStage.ANALYZE,
    ],
    CoTDepth.STANDARD: [
        ThoughtStage.DECOMPOSE,
        ThoughtStage.ANALYZE,
        ThoughtStage.SYNTHESIZE,
    ],
    CoTDepth.DEEP: [
        ThoughtStage.DECOMPOSE,
        ThoughtStage.CONTEXTUALIZE,
        ThoughtStage.ANALYZE,
        ThoughtStage.SYNTHESIZE,
        ThoughtStage.VALIDATE,
    ],
    CoTDepth.EXPERT: [
        ThoughtStage.DECOMPOSE,
        ThoughtStage.CONTEXTUALIZE,
        ThoughtStage.ANALYZE,
        ThoughtStage.SYNTHESIZE,
        ThoughtStage.VALIDATE,
        ThoughtStage.CORRECT,
        ThoughtStage.REFLECT,
    ],
}

STAGE_LABELS: Dict[ThoughtStage, str] = {
    ThoughtStage.DECOMPOSE:     "Mengurai masalah",
    ThoughtStage.CONTEXTUALIZE: "Membaca konteks & perasaan",
    ThoughtStage.ANALYZE:       "Menganalisis mendalam",
    ThoughtStage.SYNTHESIZE:    "Menyusun jawaban",
    ThoughtStage.VALIDATE:      "Memvalidasi kualitas",
    ThoughtStage.CORRECT:       "Memperbaiki kelemahan",
    ThoughtStage.REFLECT:       "Refleksi akhir",
}

STAGE_EMOJI: Dict[ThoughtStage, str] = {
    ThoughtStage.DECOMPOSE:     "🔍",
    ThoughtStage.CONTEXTUALIZE: "💭",
    ThoughtStage.ANALYZE:       "🧠",
    ThoughtStage.SYNTHESIZE:    "⚡",
    ThoughtStage.VALIDATE:      "✅",
    ThoughtStage.CORRECT:       "🔧",
    ThoughtStage.REFLECT:       "🪞",
}


def auto_depth(spec) -> CoTDepth:
    """
    Pilih CoTDepth otomatis berdasarkan TaskSpecification.
    Mapping yang sama dengan routing orchestrator.py.
    """
    complexity  = getattr(spec, "complexity_score",    0.3)
    is_simple   = getattr(spec, "is_simple",           True)
    multi_agent = getattr(spec, "requires_multi_agent", False)
    intent      = getattr(spec, "primary_intent",      "general")

    # Multi-agent / proyek penuh → EXPERT
    if multi_agent:
        return CoTDepth.EXPERT

    # Intent yang selalu butuh reasoning dalam
    deep_intents = {"coding", "system", "analysis", "research", "planning"}
    if intent in deep_intents and complexity >= 0.5:
        return CoTDepth.DEEP

    if complexity >= 0.75:
        return CoTDepth.EXPERT
    if complexity >= 0.5:
        return CoTDepth.DEEP
    if complexity >= 0.25 or not is_simple:
        return CoTDepth.STANDARD

    return CoTDepth.FAST


# ══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ThoughtStep:
    stage:       str
    label:       str
    raw_output:  str            # JSON mentah dari LLM
    parsed:      Dict           # Hasil parse JSON (kosong jika gagal)
    confidence:  float
    duration_ms: int


@dataclass
class CoTResult:
    question:           str
    depth:              str
    enriched_prompt:    str     # System prompt yang diperkaya CoT → diteruskan ke orchestrator
    final_answer:       str     # Jawaban final (untuk FAST path atau fallback)
    thought_trace:      List[ThoughtStep]
    overall_confidence: float
    total_duration_ms:  int
    used_correction:    bool  = False
    correction_note:    str   = ""
    meta:               Dict  = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
# PER-STAGE SYSTEM PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

STAGE_PROMPTS: Dict[ThoughtStage, str] = {

    ThoughtStage.DECOMPOSE: """Kamu adalah modul DEKOMPOSISI dalam sistem penalaran Orchestra.

Tugasmu: Urai permintaan pengguna menjadi sub-komponen yang dapat dikerjakan.

Lakukan:
1. Identifikasi SEMUA sub-masalah tersembunyi dalam permintaan ini
2. Tentukan urutan logis pengerjaan (mana yang harus duluan)
3. Tandai komponen paling kritis
4. Perkirakan kompleksitas nyata (bukan hanya panjang teks)

Output HANYA JSON valid, tidak ada teks lain:
{
  "sub_problems": ["sub-masalah 1", "sub-masalah 2"],
  "critical_path": ["komponen kritis pertama", "komponen kritis kedua"],
  "hidden_requirements": ["syarat tersembunyi yang tidak eksplisit disebutkan"],
  "complexity_note": "catatan tentang kompleksitas sebenarnya",
  "estimated_depth": "trivial|simple|moderate|complex|expert",
  "confidence": 0.0
}""",

    ThoughtStage.CONTEXTUALIZE: """Kamu adalah modul KONTEKSTUALISASI dalam sistem penalaran Orchestra.

Tugasmu: Pahami siapa yang bertanya dan dalam kondisi apa.

Analisis:
1. Kondisi emosional pengguna (dari nada, pilihan kata, tanda baca)
2. Apa yang TIDAK diucapkan tapi tersirat
3. Tone respons yang paling tepat
4. Asumsi yang perlu dikonfirmasi atau diabaikan
5. Bagaimana history percakapan mempengaruhi konteks ini

Output HANYA JSON valid:
{
  "user_state": "deskripsi kondisi pengguna saat ini",
  "emotional_cues": ["tanda emosi 1", "tanda emosi 2"],
  "implied_need": "apa yang sebenarnya dibutuhkan (bukan hanya diminta)",
  "tone_recommendation": "warm|direct|enthusiastic|calm|professional|empathetic",
  "critical_assumptions": ["asumsi kritis yang harus diperhatikan"],
  "context_from_history": "ringkasan konteks relevan dari percakapan sebelumnya",
  "confidence": 0.0
}""",

    ThoughtStage.ANALYZE: """Kamu adalah modul ANALISIS MENDALAM dalam sistem penalaran Orchestra.

Tugasmu: Analisis setiap sub-masalah secara menyeluruh dengan perspektif yang luas.

Untuk setiap sub-masalah:
1. Pertimbangkan SEMUA pendekatan yang mungkin (minimal 2-3)
2. Evaluasi trade-off setiap pendekatan
3. Pilih yang terbaik dengan alasan konkret
4. Identifikasi potensi edge cases dan risiko
5. Tambahkan insight yang mungkin tidak terpikirkan pengguna

Output HANYA JSON valid:
{
  "analyses": [
    {
      "sub_problem": "nama sub-masalah",
      "approaches": [
        {"name": "pendekatan A", "pros": ["pro1"], "cons": ["con1"]},
        {"name": "pendekatan B", "pros": ["pro1"], "cons": ["con1"]}
      ],
      "chosen": "pendekatan terpilih",
      "reasoning": "alasan memilih pendekatan ini",
      "edge_cases": ["edge case 1"],
      "risks": ["risiko 1"]
    }
  ],
  "key_insights": ["insight penting yang mungkin terlewat pengguna"],
  "prerequisite_knowledge": ["hal yang perlu dipahami sebelum menjawab"],
  "confidence": 0.0
}""",

    ThoughtStage.SYNTHESIZE: """Kamu adalah modul SINTESIS dalam sistem penalaran Orchestra.

Tugasmu: Gabungkan semua analisis menjadi jawaban yang kohesif, lengkap, dan manusiawi.

Aturan WAJIB:
- JANGAN mulai dengan "Tentu!", "Baik!", "Berikut adalah...", atau frasa robotik apapun
- Jika pengguna dalam kondisi emosional (frustrasi/lelah), akui dulu sebelum solusi
- Jawab seperti manusia yang benar-benar memahami dan peduli
- Pastikan semua sub-masalah terjawab, tapi tidak redundan
- Gunakan tone yang direkomendasikan dari tahap kontekstualisasi
- Kode/teknis: tetap presisi, jangan simplifikasi berlebihan

Output HANYA JSON valid:
{
  "draft_answer": "jawaban lengkap dalam bahasa alami (boleh panjang)",
  "tone_used": "tone yang digunakan",
  "acknowledgment_included": true,
  "all_subproblems_addressed": true,
  "key_points": ["poin utama 1", "poin utama 2"],
  "confidence": 0.0
}""",

    ThoughtStage.VALIDATE: """Kamu adalah modul VALIDASI KRITIS dalam sistem penalaran Orchestra.

Tugasmu: Cek jawaban draft dengan standar tinggi — jujur dan tanpa kompromi.

Pertanyaan validasi (jawab jujur):
1. Apakah jawaban menjawab SEMUA aspek pertanyaan?
2. Adakah informasi yang tidak akurat atau menyesatkan?
3. Adakah aspek penting yang terlewat?
4. Apakah tone sudah sesuai kondisi emosional pengguna?
5. Apakah ada yang terlalu panjang, terlalu pendek, atau generik?
6. Apakah ada asumsi yang salah?

Output HANYA JSON valid:
{
  "all_aspects_covered": true,
  "has_inaccuracies": false,
  "missing_aspects": ["aspek yang kurang (kosong jika tidak ada)"],
  "wrong_assumptions": ["asumsi yang salah (kosong jika tidak ada)"],
  "tone_appropriate": true,
  "length_appropriate": true,
  "needs_correction": false,
  "correction_priority": "none|low|medium|high",
  "correction_notes": "catatan spesifik apa yang perlu diperbaiki",
  "confidence": 0.0
}""",

    ThoughtStage.CORRECT: """Kamu adalah modul KOREKSI dalam sistem penalaran Orchestra.

Tugasmu: Perbaiki jawaban berdasarkan temuan validasi. Buat versi yang lebih baik.

Lakukan:
1. Perbaiki SEMUA kesalahan yang ditemukan di tahap validasi
2. Tambahkan aspek yang terlewat
3. Sesuaikan tone jika perlu
4. Pastikan perbaikan tidak menghilangkan bagian yang sudah baik
5. Verifikasi ulang bahwa perbaikan tidak menciptakan masalah baru

Output HANYA JSON valid:
{
  "corrections_made": ["koreksi 1: apa yang diubah dan mengapa", "koreksi 2"],
  "improved_answer": "jawaban yang sudah diperbaiki secara menyeluruh",
  "improvement_summary": "ringkasan singkat apa yang diperbaiki",
  "confidence": 0.0
}""",

    ThoughtStage.REFLECT: """Kamu adalah modul REFLEKSI AKHIR dalam sistem penalaran Orchestra.

Ini adalah pemeriksaan terakhir — perspektif manusia bijak yang benar-benar peduli.

Pertanyaan refleksi (jawab jujur):
1. Jika ini adalah percakapan nyata antara manusia, apakah jawaban ini sudah membantu?
2. Adakah sesuatu yang secara intuitif terasa kurang tepat?
3. Apakah jawaban ini akan membuat pengguna lebih pintar atau lebih berdaya?
4. Apakah ada yang bisa ditambahkan yang sangat berharga tapi belum ada?
5. Apakah kamu bangga dengan jawaban ini?

Output HANYA JSON valid:
{
  "reflection": "refleksi jujur tentang kualitas dan dampak jawaban",
  "human_value_assessment": "apakah ini benar-benar membantu manusia",
  "final_tweaks": ["penyesuaian kecil terakhir jika ada"],
  "final_answer": "jawaban final yang sudah sempurna",
  "overall_quality": "excellent|good|acceptable|needs_work",
  "confidence": 0.0
}""",
}


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: should_use_cot
# ══════════════════════════════════════════════════════════════════════════════

def should_use_cot(spec) -> bool:
    """
    Tentukan apakah request ini perlu diproses dengan CoT.
    Dipanggil dari orchestrator.py sebelum pipeline utama.

    Bypass CoT untuk:
    - Request trivial (is_simple + complexity < 0.2)
    - Vision (sudah punya pipeline sendiri)
    - Image/audio generation (tidak butuh reasoning)
    - Saat ada foto/gambar diupload
    """
    if not spec:
        return False

    intent     = getattr(spec, "primary_intent",   "general")
    is_simple  = getattr(spec, "is_simple",         True)
    complexity = getattr(spec, "complexity_score",  0.0)

    # Intent yang di-bypass
    bypass_intents = {"vision", "image_generation", "audio_generation"}
    if intent in bypass_intents:
        return False

    # Benar-benar trivial → bypass
    if is_simple and complexity < 0.2:
        return False

    return True


# ══════════════════════════════════════════════════════════════════════════════
# CHAIN OF THOUGHT ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ChainOfThoughtEngine:
    """
    Mesin penalaran bertahap untuk Orchestra.

    Alur integrasi dengan orchestrator.py:
    1. Dipanggil setelah PHASE 1 (preprocessing) selesai
    2. Menghasilkan `enriched_prompt` → dipakai sebagai system_prompt di PHASE 5+
    3. Melaporkan progress via OrchestratorEvent → diteruskan ke SSE stream
    """

    async def stream_reason(
        self,
        spec,                           # TaskSpecification dari request_preprocessor
        history:       List[Dict] = None,
        system_prompt: str        = "",
        depth:         Optional[CoTDepth] = None,
        model_override: str       = "",  # Paksa model tertentu untuk CoT
    ) -> AsyncGenerator[Any, None]:
        """
        Entry point utama. Generator yang menghasilkan OrchestratorEvent.

        Event types yang dikirim:
        - "status"   → progress info ke UI
        - "cot_done" → selesai, data berisi enriched_prompt + CoTResult

        Contoh di orchestrator.py:
            async for event in cot_engine.stream_reason(spec=spec, history=history, system_prompt=system_prompt):
                if event.type == "cot_done":
                    system_prompt = event.data["enriched_prompt"]
                    cot_result = event.data["cot_result"]
                else:
                    yield event  # forward status ke frontend
        """
        # Import OrchestratorEvent dari orchestrator (lazy import agar tidak circular)
        from core.orchestrator import OrchestratorEvent

        start_total = time.time()
        history = history or []

        # ── Pilih depth ──────────────────────────────────────────────────────
        selected_depth = depth or auto_depth(spec)
        stages = DEPTH_STAGES[selected_depth]
        question = getattr(spec, "original_message", "")

        yield OrchestratorEvent("status",
            f"🧠 CoT Engine aktif — mode: {selected_depth.value.upper()} "
            f"({len(stages)} tahap)")

        # ── Siapkan konteks ──────────────────────────────────────────────────
        emotional_hint = self._build_emotional_hint(spec)
        history_summary = self._summarize_history(history)

        # ── Pilih model untuk CoT ────────────────────────────────────────────
        cot_model = await self._select_cot_model(model_override)

        log.info("CoT started",
                 depth=selected_depth.value,
                 stages=[s.value for s in stages],
                 model=cot_model,
                 question_len=len(question))

        # ── Jalankan setiap tahap ────────────────────────────────────────────
        thought_trace: List[ThoughtStep] = []
        stage_results: Dict[str, Any]    = {}
        used_correction = False
        correction_note = ""

        for stage in stages:
            emoji = STAGE_EMOJI.get(stage, "•")
            label = STAGE_LABELS.get(stage, stage.value)

            yield OrchestratorEvent("status", f"  {emoji} {label}...")

            step = await self._run_stage(
                stage          = stage,
                question       = question,
                history_summary= history_summary,
                emotional_hint = emotional_hint,
                stage_results  = stage_results,
                cot_model      = cot_model,
            )
            thought_trace.append(step)
            stage_results[stage.value] = step.parsed or {"raw": step.raw_output}

            # Cek apakah perlu self-correction
            if stage == ThoughtStage.VALIDATE:
                needs_fix = step.parsed.get("needs_correction", False)
                priority  = step.parsed.get("correction_priority", "none")
                if needs_fix and priority in ("medium", "high"):
                    yield OrchestratorEvent("status",
                        f"  🔧 Validasi menemukan kelemahan ({priority}) — menjalankan koreksi...")
                elif not needs_fix:
                    # Skip CORRECT + REFLECT jika tidak perlu
                    if selected_depth == CoTDepth.EXPERT:
                        yield OrchestratorEvent("status",
                            "  ✅ Validasi lulus — koreksi tidak diperlukan")

            if stage == ThoughtStage.CORRECT:
                used_correction = True
                correction_note = step.parsed.get("improvement_summary", "")

        # ── Hitung confidence keseluruhan ────────────────────────────────────
        confidences = [s.confidence for s in thought_trace if s.confidence > 0]
        overall_conf = sum(confidences) / len(confidences) if confidences else 0.7

        # ── Ekstrak jawaban final ────────────────────────────────────────────
        final_answer = self._extract_final_answer(stage_results, stages)

        # ── Bangun enriched_prompt ───────────────────────────────────────────
        # Ini adalah output UTAMA CoT: system_prompt yang diperkaya dengan
        # insight dari semua tahap reasoning — diteruskan ke orchestrator
        # sebagai context untuk agent executor / model final.
        enriched_prompt = self._build_enriched_prompt(
            base_system_prompt = system_prompt,
            stage_results      = stage_results,
            stages             = stages,
            emotional_hint     = emotional_hint,
            final_answer       = final_answer,
            depth              = selected_depth,
        )

        total_ms = int((time.time() - start_total) * 1000)

        log.info("CoT complete",
                 depth=selected_depth.value,
                 stages_run=len(stages),
                 confidence=round(overall_conf, 2),
                 total_ms=total_ms,
                 answer_preview=final_answer[:80])

        result = CoTResult(
            question           = question,
            depth              = selected_depth.value,
            enriched_prompt    = enriched_prompt,
            final_answer       = final_answer,
            thought_trace      = thought_trace,
            overall_confidence = overall_conf,
            total_duration_ms  = total_ms,
            used_correction    = used_correction,
            correction_note    = correction_note,
        )

        # Summary untuk UI
        yield OrchestratorEvent("status",
            f"  🎯 CoT selesai — confidence: {overall_conf:.0%} | "
            f"{total_ms}ms | {len(stages)} tahap"
        )

        # Event akhir: bawa CoTResult + enriched_prompt
        yield OrchestratorEvent("cot_done", "", {
            "enriched_prompt":    enriched_prompt,
            "final_answer":       final_answer,
            "cot_result":         result,
            "confidence":         round(overall_conf, 2),
            "depth":              selected_depth.value,
            "stages_run":         len(stages),
            "total_ms":           total_ms,
            "used_correction":    used_correction,
        })

    # ── Stage Runner ─────────────────────────────────────────────────────────

    async def _run_stage(
        self,
        stage:          ThoughtStage,
        question:       str,
        history_summary: str,
        emotional_hint: str,
        stage_results:  Dict[str, Any],
        cot_model:      str,
    ) -> ThoughtStep:
        t_start = time.time()

        system_prompt = STAGE_PROMPTS[stage]
        user_prompt   = self._build_user_prompt(
            stage, question, history_summary, emotional_hint, stage_results
        )

        raw = await self._call_model(
            system    = system_prompt,
            user      = user_prompt,
            model     = cot_model,
            stage     = stage,
        )

        parsed     = self._parse_json(raw)
        confidence = float(parsed.get("confidence", 0.7)) if parsed else 0.5
        duration   = int((time.time() - t_start) * 1000)

        log.debug("CoT stage", stage=stage.value,
                  confidence=confidence, duration_ms=duration)

        return ThoughtStep(
            stage       = stage.value,
            label       = STAGE_LABELS.get(stage, stage.value),
            raw_output  = raw,
            parsed      = parsed,
            confidence  = confidence,
            duration_ms = duration,
        )

    # ── Model Caller — menggunakan model_manager.chat_completion() ──────────

    async def _call_model(
        self,
        system: str,
        user:   str,
        model:  str,
        stage:  ThoughtStage,
    ) -> str:
        """
        Panggil model menggunakan model_manager.chat_completion() — interface
        yang sama dengan yang dipakai di seluruh orchestrator.py.
        """
        from core.model_manager import model_manager

        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ]

        # Hemat token: CoT tidak butuh output panjang per tahap
        # SYNTHESIZE dan CORRECT/REFLECT butuh token lebih banyak
        max_tok = 600
        if stage in (ThoughtStage.SYNTHESIZE, ThoughtStage.CORRECT, ThoughtStage.REFLECT):
            max_tok = 1200

        try:
            result = await asyncio.wait_for(
                model_manager.chat_completion(
                    model       = model,
                    messages    = messages,
                    temperature = 0.15,   # Rendah → konsistensi tinggi untuk reasoning
                    max_tokens  = max_tok,
                ),
                timeout=20.0,
            )
            return result or ""
        except asyncio.TimeoutError:
            log.warning("CoT stage timeout", stage=stage.value, model=model)
            return self._fallback_json(stage)
        except Exception as e:
            log.warning("CoT stage error", stage=stage.value, error=str(e)[:80])
            return self._fallback_json(stage)

    # ── Prompt Builder ────────────────────────────────────────────────────────

    def _build_user_prompt(
        self,
        stage:          ThoughtStage,
        question:       str,
        history_summary: str,
        emotional_hint: str,
        stage_results:  Dict[str, Any],
    ) -> str:
        parts = []

        parts.append(f"=== PERTANYAAN / TUGAS ===\n{question}")

        if history_summary:
            parts.append(f"=== KONTEKS PERCAKAPAN ===\n{history_summary}")

        if emotional_hint:
            parts.append(f"=== KONDISI PENGGUNA ===\n{emotional_hint}")

        # Sertakan hasil tahap sebelumnya secara selektif (hemat token)
        prev_order = [
            ThoughtStage.DECOMPOSE,
            ThoughtStage.CONTEXTUALIZE,
            ThoughtStage.ANALYZE,
            ThoughtStage.SYNTHESIZE,
            ThoughtStage.VALIDATE,
            ThoughtStage.CORRECT,
        ]

        relevant_prev = []
        for prev in prev_order:
            if prev == stage:
                break
            if prev.value in stage_results:
                data = stage_results[prev.value]
                label = STAGE_LABELS.get(prev, prev.value)
                # Serialize dengan batas karakter
                serialized = json.dumps(data, ensure_ascii=False)
                if len(serialized) > 800:
                    serialized = serialized[:800] + "...[dipotong]"
                relevant_prev.append(f"[{label}]:\n{serialized}")

        if relevant_prev:
            parts.append("=== HASIL TAHAP SEBELUMNYA ===\n" + "\n\n".join(relevant_prev))

        label = STAGE_LABELS.get(stage, stage.value)
        parts.append(f"=== TUGASMU ===\nJalankan tahap: {label}\nOutput HANYA JSON valid.")

        return "\n\n".join(parts)

    # ── Build Enriched Prompt ─────────────────────────────────────────────────

    def _build_enriched_prompt(
        self,
        base_system_prompt: str,
        stage_results:      Dict[str, Any],
        stages:             List[ThoughtStage],
        emotional_hint:     str,
        final_answer:       str,
        depth:              CoTDepth,
    ) -> str:
        """
        Bangun system_prompt yang diperkaya dengan insight dari CoT.
        Ini yang diteruskan ke agent executor / model final di orchestrator.

        Struktur:
        [Base system prompt] + [CoT Intelligence Briefing]

        Intelligence Briefing berisi:
        - Kontekstualisasi kondisi pengguna
        - Insight kunci dari analisis
        - Poin-poin yang harus dicakup
        - Instruksi tone
        - (Jika EXPERT) Draft jawaban final dari refleksi
        """
        sections = [base_system_prompt] if base_system_prompt else []

        briefing_parts = []
        briefing_parts.append(
            "\n\n[═══ INTELLIGENCE BRIEFING DARI CoT ENGINE ═══]\n"
            "Berikut adalah hasil analisis mendalam yang sudah dilakukan. "
            "Gunakan ini sebagai fondasi untuk merespons pengguna."
        )

        # Konteks pengguna (dari CONTEXTUALIZE)
        ctx = stage_results.get(ThoughtStage.CONTEXTUALIZE.value, {})
        if ctx:
            user_state = ctx.get("user_state", "")
            tone_rec   = ctx.get("tone_recommendation", "balanced")
            implied    = ctx.get("implied_need", "")
            ack_needed = ctx.get("acknowledgment_needed", False)

            user_ctx = []
            if user_state:
                user_ctx.append(f"Kondisi pengguna: {user_state}")
            if implied:
                user_ctx.append(f"Kebutuhan tersirat: {implied}")
            if tone_rec:
                user_ctx.append(f"Gunakan tone: {tone_rec}")
            if ack_needed:
                user_ctx.append(
                    "⚠️ PENTING: Akui kondisi emosional pengguna SEBELUM memberikan solusi."
                )
            if user_ctx:
                briefing_parts.append("\n📌 KONTEKS PENGGUNA:\n" + "\n".join(f"• {c}" for c in user_ctx))

        # Insight dari ANALYZE
        ana = stage_results.get(ThoughtStage.ANALYZE.value, {})
        if ana:
            insights = ana.get("key_insights", [])
            if insights:
                briefing_parts.append(
                    "\n💡 INSIGHT KUNCI:\n" +
                    "\n".join(f"• {i}" for i in insights[:5])
                )
            # Chosen approaches per sub-problem
            analyses = ana.get("analyses", [])
            if analyses:
                approach_lines = []
                for a in analyses[:4]:
                    sp = a.get("sub_problem", "")
                    chosen = a.get("chosen", "")
                    reasoning = a.get("reasoning", "")
                    if sp and chosen:
                        approach_lines.append(f"• [{sp}] → {chosen}: {reasoning[:100]}")
                if approach_lines:
                    briefing_parts.append(
                        "\n🎯 PENDEKATAN TERPILIH:\n" + "\n".join(approach_lines)
                    )

        # Key points dari SYNTHESIZE
        syn = stage_results.get(ThoughtStage.SYNTHESIZE.value, {})
        if syn:
            key_points = syn.get("key_points", [])
            if key_points:
                briefing_parts.append(
                    "\n✅ POIN YANG HARUS DICAKUP:\n" +
                    "\n".join(f"• {p}" for p in key_points[:6])
                )

        # Temuan VALIDATE (jika ada kelemahan)
        val = stage_results.get(ThoughtStage.VALIDATE.value, {})
        if val:
            missing = val.get("missing_aspects", [])
            wrong   = val.get("wrong_assumptions", [])
            if missing:
                briefing_parts.append(
                    "\n⚠️ JANGAN TERLEWAT:\n" +
                    "\n".join(f"• {m}" for m in missing[:3])
                )
            if wrong:
                briefing_parts.append(
                    "\n❌ HINDARI ASUMSI INI:\n" +
                    "\n".join(f"• {w}" for w in wrong[:3])
                )

        # Untuk EXPERT: sertakan draft final dari REFLECT/CORRECT sebagai panduan
        ref = stage_results.get(ThoughtStage.REFLECT.value, {})
        cor = stage_results.get(ThoughtStage.CORRECT.value, {})

        if depth == CoTDepth.EXPERT and (ref or cor):
            expert_answer = (
                ref.get("final_answer", "") or
                cor.get("improved_answer", "") or
                final_answer
            )
            if expert_answer and len(expert_answer) > 50:
                # Di EXPERT mode, CoT sudah punya jawaban berkualitas tinggi.
                # Beri sebagai "template" — model final bisa kembangkan.
                briefing_parts.append(
                    "\n🏆 DRAFT JAWABAN (dari CoT EXPERT — gunakan sebagai acuan):\n"
                    f"{expert_answer[:1500]}"
                    + ("\n...[dipotong, kembangkan sesuai konteks]" if len(expert_answer) > 1500 else "")
                )
        elif final_answer and len(final_answer) > 50:
            # DEEP/STANDARD: sertakan sebagai guidance
            briefing_parts.append(
                "\n📝 PANDUAN JAWABAN (dari CoT):\n"
                f"{final_answer[:800]}"
                + ("\n...[kembangkan jika perlu]" if len(final_answer) > 800 else "")
            )

        briefing_parts.append("\n[═══ AKHIR BRIEFING CoT ═══]\n")

        sections.append("".join(briefing_parts))
        return "\n".join(sections)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_emotional_hint(self, spec) -> str:
        """Konversi EmotionalState ke teks untuk CoT prompt."""
        es = getattr(spec, "emotional_state", None)
        if not es:
            return ""

        lines = []
        emotion   = getattr(es, "dominant_emotion",    "neutral")
        intensity = getattr(es, "intensity",            0.0)
        need      = getattr(es, "implied_need",         "none")
        tone      = getattr(es, "tone_hint",            "balanced")
        needs_ack = getattr(es, "needs_acknowledgment", False)
        time_p    = getattr(es, "has_time_pressure",    False)
        signals   = getattr(es, "detected_signals",     [])

        if emotion != "neutral" and intensity > 0.1:
            lines.append(f"Emosi: {emotion} (intensitas {intensity:.0%})")
        if need != "none":
            lines.append(f"Kebutuhan tersirat: {need}")
        if needs_ack:
            lines.append("⚠️ Butuh validasi emosional sebelum solusi")
        if time_p:
            lines.append("⚠️ Ada tekanan waktu — jawaban harus ringkas & langsung")
        if tone != "balanced":
            lines.append(f"Tone: {tone}")
        if signals:
            lines.append(f"Sinyal terdeteksi: {', '.join(signals[:5])}")

        return "\n".join(lines) if lines else ""

    def _summarize_history(self, history: List[Dict]) -> str:
        """Ringkasan singkat history — hemat token."""
        if not history:
            return ""
        recent = history[-6:]
        lines  = []
        for m in recent:
            role    = "Pengguna" if m.get("role") == "user" else "Orchestra"
            content = m.get("content", "")
            if len(content) > 120:
                content = content[:120] + "..."
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _parse_json(self, raw: str) -> Dict:
        """Parse JSON dari output LLM secara aman."""
        if not raw:
            return {}
        clean = raw.strip()
        # Strip markdown code blocks
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # Coba ekstrak objek JSON pertama dengan regex
            match = re.search(r'\{.*\}', clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        return {}

    def _extract_final_answer(
        self,
        stage_results: Dict[str, Any],
        stages:        List[ThoughtStage],
    ) -> str:
        """Ekstrak jawaban terbaik dari hasil tahap."""
        priority = [
            (ThoughtStage.REFLECT,    "final_answer"),
            (ThoughtStage.CORRECT,    "improved_answer"),
            (ThoughtStage.SYNTHESIZE, "draft_answer"),
            (ThoughtStage.ANALYZE,    None),
        ]
        for stage, key in priority:
            if stage.value not in stage_results:
                continue
            data = stage_results[stage.value]
            if key and isinstance(data, dict):
                ans = data.get(key, "")
                if ans and len(str(ans)) > 20:
                    return str(ans)
            elif isinstance(data, dict):
                # Fallback: cari field apapun yang panjang
                for v in data.values():
                    if isinstance(v, str) and len(v) > 50:
                        return v
        return ""

    async def _select_cot_model(self, override: str = "") -> str:
        """
        Pilih model untuk CoT reasoning.
        Prioritas: override → model BRAIN/reasoning → default model.
        Menggunakan model_manager.available_models langsung.
        """
        from core.model_manager import model_manager

        if override and override in model_manager.available_models:
            return override

        # Cari model reasoning terkuat yang tersedia
        # Urutan preferensi berdasarkan kemampuan reasoning
        reasoning_preferences = [
            # OpenAI
            "o4-mini", "o3-mini", "gpt-4.1", "gpt-4o", "gpt-4-turbo",
            # Anthropic
            "claude-sonnet-4-5", "claude-opus-4-5", "claude-haiku-4-5",
            # Google
            "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash",
            # Sumopod / custom — cek prefix
            "deepseek", "qwen", "llama",
        ]

        available = list(model_manager.available_models.keys())

        for pref in reasoning_preferences:
            for m in available:
                if pref in m.lower():
                    log.debug("CoT model selected", model=m, via="preference")
                    return m

        # Ultimate fallback: model pertama yang tersedia
        default = model_manager.get_default_model()
        log.debug("CoT model selected", model=default, via="default")
        return default

    def _fallback_json(self, stage: ThoughtStage) -> str:
        """JSON fallback jika model gagal dipanggil."""
        fallbacks = {
            ThoughtStage.DECOMPOSE:
                '{"sub_problems":["pertanyaan utama"],"critical_path":["jawab langsung"],'
                '"hidden_requirements":[],"complexity_note":"tidak dapat dianalisis","estimated_depth":"simple","confidence":0.4}',
            ThoughtStage.CONTEXTUALIZE:
                '{"user_state":"tidak dapat dianalisis","emotional_cues":[],'
                '"implied_need":"none","tone_recommendation":"balanced","critical_assumptions":[],'
                '"context_from_history":"","confidence":0.4}',
            ThoughtStage.ANALYZE:
                '{"analyses":[{"sub_problem":"pertanyaan","approaches":['
                '{"name":"jawab langsung","pros":["efisien"],"cons":[]}],'
                '"chosen":"jawab langsung","reasoning":"fallback","edge_cases":[],"risks":[]}],'
                '"key_insights":[],"prerequisite_knowledge":[],"confidence":0.4}',
            ThoughtStage.SYNTHESIZE:
                '{"draft_answer":"","tone_used":"balanced","acknowledgment_included":false,'
                '"all_subproblems_addressed":false,"key_points":[],"confidence":0.4}',
            ThoughtStage.VALIDATE:
                '{"all_aspects_covered":true,"has_inaccuracies":false,"missing_aspects":[],'
                '"wrong_assumptions":[],"tone_appropriate":true,"length_appropriate":true,'
                '"needs_correction":false,"correction_priority":"none","correction_notes":"","confidence":0.5}',
            ThoughtStage.CORRECT:
                '{"corrections_made":[],"improved_answer":"","improvement_summary":"tidak ada koreksi","confidence":0.4}',
            ThoughtStage.REFLECT:
                '{"reflection":"fallback","human_value_assessment":"unknown","final_tweaks":[],'
                '"final_answer":"","overall_quality":"acceptable","confidence":0.4}',
        }
        return fallbacks.get(stage, '{"confidence":0.4}')


# ══════════════════════════════════════════════════════════════════════════════
# FORMAT UNTUK UI — Thinking Panel
# ══════════════════════════════════════════════════════════════════════════════

def format_cot_for_ui(result: CoTResult) -> Dict:
    """
    Format CoTResult untuk dikirim ke frontend sebagai 'thinking panel'.

    Contoh penggunaan di chat.py endpoint:
        ui_thinking = format_cot_for_ui(cot_result)
        response_data["thinking"] = ui_thinking
    """
    return {
        "depth":           result.depth,
        "confidence":      round(result.overall_confidence, 2),
        "total_stages":    result.total_stages if hasattr(result, "total_stages") else len(result.thought_trace),
        "duration_ms":     result.total_duration_ms,
        "self_corrected":  result.used_correction,
        "correction_note": result.correction_note,
        "stages": [
            {
                "stage":       s.stage,
                "label":       s.label,
                "duration_ms": s.duration_ms,
                "confidence":  round(s.confidence, 2),
            }
            for s in result.thought_trace
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════════════════════

cot_engine = ChainOfThoughtEngine()
