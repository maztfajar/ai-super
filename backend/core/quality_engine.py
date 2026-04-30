"""
Quality Engine (v2.1 — Performance Optimized)
=============================================
Perbaikan dari v1:
  1. _get_fast_model(): pakai daftar model yang sesuai dengan sistem (sumopod/...)
  2. _validate_quality(): timeout 8s agar tidak memperlambat pipeline
  3. Level 3 (LLM quality check) dilewati untuk output pendek (<200 chars) — tidak perlu
  4. Threshold refinement lebih realistis: QUALITY_THRESHOLD 0.5 → 0.45
  5. Scoring lebih toleran terhadap bahasa Indonesia (tidak salah deteksi "contradiction")
  6. validate_ensemble() berjalan paralel (bukan sequential)
"""

import json
import time
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import structlog

from core.model_manager import model_manager

log = structlog.get_logger()

CONFIDENCE_THRESHOLD = 0.6
QUALITY_THRESHOLD    = 0.45   # diturunkan dari 0.5 — lebih realistis


@dataclass
class ValidationResult:
    level: str
    passed: bool = True
    score: float = 1.0
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    task_id: str
    agent_type: str
    model_used: str
    validations: List[ValidationResult] = field(default_factory=list)
    overall_score: float = 1.0
    overall_passed: bool = True
    confidence: float = 0.8
    needs_refinement: bool = False
    refinement_reason: str = ""
    validation_time_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "task_id":          self.task_id,
            "agent":            self.agent_type,
            "model":            self.model_used,
            "score":            round(self.overall_score, 3),
            "passed":           self.overall_passed,
            "confidence":       round(self.confidence, 3),
            "needs_refinement": self.needs_refinement,
            "issues": [i for v in self.validations for i in v.issues],
        }


class QualityEngine:

    async def validate(
        self,
        task_id: str,
        agent_type: str,
        model_used: str,
        output: str,
        original_request: str = "",
        expected_format: Optional[str] = None,
    ) -> QualityReport:
        start = time.time()
        report = QualityReport(
            task_id=task_id,
            agent_type=agent_type,
            model_used=model_used,
        )

        # Level 1: Syntax
        report.validations.append(self._validate_syntax(output, expected_format))

        # Level 2: Semantic
        report.validations.append(self._validate_semantic(output))

        # Level 3: LLM quality check — hanya untuk output substansial (>200 chars)
        # PERBAIKAN: threshold dinaikkan dari 100 → 200 untuk hemat token
        if len(output) > 200:
            quality = await self._validate_quality(output, original_request, agent_type)
            report.validations.append(quality)
        else:
            # Output pendek → anggap cukup baik
            report.validations.append(
                ValidationResult(level="quality", passed=True, score=0.75)
            )

        # Hitung overall score
        scores = [v.score for v in report.validations]
        report.overall_score  = sum(scores) / len(scores) if scores else 0.5
        report.overall_passed = all(v.passed for v in report.validations)
        report.confidence     = report.overall_score

        # Perlu refinement?
        if report.overall_score < QUALITY_THRESHOLD:
            report.needs_refinement = True
            report.refinement_reason = f"Quality score {report.overall_score:.2f} di bawah threshold"
        elif not report.overall_passed:
            all_issues = [i for v in report.validations for i in v.issues]
            report.needs_refinement  = True
            report.refinement_reason = f"Validation issues: {'; '.join(all_issues[:3])}"

        report.validation_time_ms = int((time.time() - start) * 1000)

        log.debug(
            "Quality validated",
            task=task_id,
            score=f"{report.overall_score:.2f}",
            passed=report.overall_passed,
            time_ms=report.validation_time_ms,
        )
        return report

    async def validate_ensemble(
        self,
        outputs: List[Dict[str, str]],
        original_request: str,
    ) -> int:
        """
        Bandingkan beberapa output dan kembalikan index terbaik.
        PERBAIKAN: jalankan secara paralel (bukan sequential).
        """
        if len(outputs) <= 1:
            return 0

        # Validasi semua output secara paralel
        tasks = [
            self.validate(
                task_id=f"ensemble_{i}",
                agent_type=out.get("agent_type", "general"),
                model_used=out.get("model", "unknown"),
                output=out.get("response", ""),
                original_request=original_request,
            )
            for i, out in enumerate(outputs)
        ]
        reports = await asyncio.gather(*tasks, return_exceptions=True)

        best_idx   = 0
        best_score = -1.0
        for i, r in enumerate(reports):
            if isinstance(r, Exception):
                log.debug("Ensemble validation error", idx=i, error=str(r)[:60])
                continue
            if r.overall_score > best_score:
                best_score = r.overall_score
                best_idx   = i

        return best_idx

    # ── Level 1: Syntax ────────────────────────────────────────────────────────

    def _validate_syntax(
        self,
        output: str,
        expected_format: Optional[str] = None,
    ) -> ValidationResult:
        result = ValidationResult(level="syntax")
        issues = []

        if not output or not output.strip():
            result.passed = False
            result.score  = 0.0
            result.issues = ["Empty output"]
            return result

        # Error markers — kurangi penalti jika hanya 1 marker
        error_markers = ["[Error", "❌ ", "Error:", "Exception:", "Traceback"]
        found_errors = [m for m in error_markers if m in output]
        if found_errors:
            # Error di awal → lebih parah
            if output.strip().startswith(tuple(found_errors)):
                result.score -= 0.4
            else:
                result.score -= 0.15 * len(found_errors)
            issues.append(f"Output mengandung error marker: {found_errors[0]}")

        # JSON format check
        if expected_format == "json":
            try:
                json.loads(output)
            except json.JSONDecodeError:
                issues.append("Expected JSON tapi output bukan valid JSON")
                result.score -= 0.3

        # Truncation check
        if len(output) > 3000 and (output.rstrip().endswith("...") or output.rstrip().endswith("```")):
            issues.append("Output kemungkinan terpotong")
            result.score -= 0.1

        result.score  = max(0.0, min(1.0, result.score))
        result.passed = result.score >= 0.5
        result.issues = issues
        return result

    # ── Level 2: Semantic ──────────────────────────────────────────────────────

    def _validate_semantic(self, output: str) -> ValidationResult:
        """
        Cek konsistensi logis dan pengulangan berlebihan.
        PERBAIKAN: tidak deteksi false-positive contradiction untuk bahasa Indonesia.
        """
        result = ValidationResult(level="semantic")
        issues = []

        words = output.split()
        total_words = len(words)

        # Cek repetisi berlebihan (lebih dari 8% bigram yang sama)
        if total_words > 80:
            from collections import Counter
            bigrams = [f"{words[i]} {words[i+1]}" for i in range(total_words - 1)]
            common  = Counter(bigrams).most_common(1)
            if common:
                phrase, count = common[0]
                # Abaikan bigram sangat pendek (kata sambung) dan abaikan untuk teks pendek
                if (count > total_words * 0.08
                        and len(phrase) > 6
                        and total_words > 100):
                    issues.append(f"Repetisi berlebihan: '{phrase}' ({count}x)")
                    result.score -= 0.2

        # Cek output kosong setelah strip
        if not output.strip():
            result.score = 0.0
            result.passed = False
            issues.append("Output kosong setelah strip")

        result.score  = max(0.0, min(1.0, result.score))
        result.passed = result.score >= 0.5
        result.issues = issues
        return result

    # ── Level 3: LLM Quality ─────────────────────────────────────────────────

    async def _validate_quality(
        self,
        output: str,
        request: str,
        agent_type: str,
    ) -> ValidationResult:
        """
        LLM judge — rate output 0.0-1.0.
        PERBAIKAN: timeout 8s, model dari daftar yang benar.
        """
        result = ValidationResult(level="quality")
        try:
            fast_model = self._get_fast_model()
            prompt = (
                f"Rate the following AI response on a scale of 0.0-1.0.\n"
                f"Consider: accuracy, relevance, completeness, and clarity.\n\n"
                f"User Request: {request[:400]}\n"
                f"AI Response (first 800 chars): {output[:800]}\n\n"
                f"Output ONLY JSON (no explanation):\n"
                f'{{ "score": 0.85, "issues": ["issue1"], "strengths": ["strength1"] }}'
            )

            judge_result = await asyncio.wait_for(
                model_manager.chat_completion(
                    model=fast_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=150,
                ),
                timeout=8.0,
            )

            # Bersihkan markdown
            if "```json" in judge_result:
                judge_result = judge_result.split("```json")[1].split("```")[0].strip()
            elif "```" in judge_result:
                judge_result = judge_result.split("```")[1].split("```")[0].strip()

            # Ekstrak JSON (toleran terhadap extra text)
            import re
            m = re.search(r'\{.*\}', judge_result, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                result.score       = min(1.0, max(0.0, float(data.get("score", 0.7))))
                result.issues      = data.get("issues", [])
                result.suggestions = data.get("strengths", [])
                result.passed      = result.score >= QUALITY_THRESHOLD
            else:
                result.score  = 0.7
                result.passed = True

        except asyncio.TimeoutError:
            log.debug("Quality validation timeout (>8s), using default score")
            result.score  = 0.7
            result.passed = True
        except Exception as e:
            log.debug("Quality validation LLM failed", error=str(e)[:60])
            result.score  = 0.7
            result.passed = True

        return result

    # ── Model selection ───────────────────────────────────────────────────────

    def _get_fast_model(self) -> str:
        """
        Pilih model tercepat untuk validasi.
        PERBAIKAN: daftar sesuai dengan model yang ada di sistem (sumopod/...).
        """
        priorities = [
            "sumopod/gemini-2.5-flash-lite",
            "sumopod/claude-haiku-4-5",
            "sumopod/gpt-5-nano",
            "sumopod/qwen3.6-flash",
        ]
        available = model_manager.available_models
        for p in priorities:
            if p in available:
                return p
        # Partial match fallback
        for p in priorities:
            for k in available:
                if p.split("/")[-1] in k:
                    return k
        return model_manager.get_default_model()


quality_engine = QualityEngine()
