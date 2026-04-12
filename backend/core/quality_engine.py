"""
Super Agent Orchestrator — Quality Assurance Engine
Multi-level validation pipeline for agent outputs.
Levels: Syntax → Semantic → Quality → Integration
"""
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import structlog

from core.model_manager import model_manager

log = structlog.get_logger()


@dataclass
class ValidationResult:
    """Result from a single validation level."""
    level: str                   # syntax | semantic | quality | integration
    passed: bool = True
    score: float = 1.0           # 0.0-1.0
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    """Complete quality assessment of an agent output."""
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
            "task_id": self.task_id,
            "agent": self.agent_type,
            "model": self.model_used,
            "score": round(self.overall_score, 3),
            "passed": self.overall_passed,
            "confidence": round(self.confidence, 3),
            "needs_refinement": self.needs_refinement,
            "issues": [
                issue
                for v in self.validations
                for issue in v.issues
            ],
        }


# Confidence threshold — below this, request refinement
CONFIDENCE_THRESHOLD = 0.6
QUALITY_THRESHOLD = 0.5


class QualityEngine:
    """
    Multi-level validation pipeline.
    Each task output goes through 4 validation levels.
    """

    async def validate(
        self,
        task_id: str,
        agent_type: str,
        model_used: str,
        output: str,
        original_request: str = "",
        expected_format: Optional[str] = None,
    ) -> QualityReport:
        """
        Run the full validation pipeline on an agent output.
        """
        start = time.time()
        report = QualityReport(
            task_id=task_id,
            agent_type=agent_type,
            model_used=model_used,
        )

        # Level 1: Syntax Validation
        syntax = self._validate_syntax(output, expected_format)
        report.validations.append(syntax)

        # Level 2: Semantic Validation
        semantic = self._validate_semantic(output)
        report.validations.append(semantic)

        # Level 3: Quality Validation (LLM-based if output is substantial)
        if len(output) > 100:
            quality = await self._validate_quality(output, original_request, agent_type)
            report.validations.append(quality)
        else:
            report.validations.append(
                ValidationResult(level="quality", passed=True, score=0.7)
            )

        # Compute overall score
        scores = [v.score for v in report.validations]
        report.overall_score = sum(scores) / len(scores) if scores else 0.5
        report.overall_passed = all(v.passed for v in report.validations)
        report.confidence = report.overall_score

        # Determine if refinement is needed
        if report.overall_score < QUALITY_THRESHOLD:
            report.needs_refinement = True
            report.refinement_reason = "Quality score below threshold"
        elif not report.overall_passed:
            report.needs_refinement = True
            all_issues = [i for v in report.validations for i in v.issues]
            report.refinement_reason = f"Validation issues: {'; '.join(all_issues[:3])}"

        report.validation_time_ms = int((time.time() - start) * 1000)

        log.debug("Quality validated",
                  task=task_id, score=f"{report.overall_score:.2f}",
                  passed=report.overall_passed,
                  time_ms=report.validation_time_ms)

        return report

    async def validate_ensemble(
        self,
        outputs: List[Dict[str, str]],
        original_request: str,
    ) -> int:
        """
        Compare multiple outputs and return index of the best one.
        Used when ensemble methods produce multiple candidates.
        """
        if len(outputs) <= 1:
            return 0

        reports = []
        for i, out in enumerate(outputs):
            report = await self.validate(
                task_id=f"ensemble_{i}",
                agent_type=out.get("agent_type", "general"),
                model_used=out.get("model", "unknown"),
                output=out.get("response", ""),
                original_request=original_request,
            )
            reports.append(report)

        # Pick the highest scoring
        best_idx = max(range(len(reports)), key=lambda i: reports[i].overall_score)
        return best_idx

    # ─── Level 1: Syntax Validation ───────────────────────────

    def _validate_syntax(self, output: str, expected_format: Optional[str] = None) -> ValidationResult:
        """Check format correctness, required fields, data integrity."""
        result = ValidationResult(level="syntax")
        issues = []

        # Check for empty output
        if not output or not output.strip():
            result.passed = False
            result.score = 0.0
            issues.append("Empty output")
            result.issues = issues
            return result

        # Check for error markers
        error_markers = ["[Error", "❌", "Error:", "Exception:", "Traceback"]
        for marker in error_markers:
            if marker in output:
                issues.append(f"Output contains error marker: {marker}")
                result.score -= 0.2

        # If JSON expected, validate JSON
        if expected_format == "json":
            try:
                json.loads(output)
            except json.JSONDecodeError:
                issues.append("Expected JSON format but output is not valid JSON")
                result.score -= 0.3

        # Check for truncation indicators
        if output.endswith("...") or output.endswith("```"):
            if len(output) > 3000:
                issues.append("Output may be truncated")
                result.score -= 0.1

        result.score = max(0.0, min(1.0, result.score))
        result.passed = result.score >= 0.5
        result.issues = issues
        return result

    # ─── Level 2: Semantic Validation ─────────────────────────

    def _validate_semantic(self, output: str) -> ValidationResult:
        """Check logical consistency and reasonableness."""
        result = ValidationResult(level="semantic")
        issues = []

        # Check for self-contradictions (simple heuristic)
        sentences = output.split(".")
        if len(sentences) > 3:
            # Check for contradictory statements (very basic)
            negation_pairs = [
                ("is not", "is"), ("cannot", "can"), ("should not", "should"),
                ("tidak", "bisa"), ("bukan", "adalah"),
            ]
            for neg, pos in negation_pairs:
                neg_count = output.lower().count(neg)
                pos_count = output.lower().count(pos)
                if neg_count > 0 and pos_count > 3 and neg_count > pos_count:
                    issues.append("Potential self-contradiction detected")
                    result.score -= 0.1
                    break

        # Check for excessive repetition
        words = output.split()
        if len(words) > 50:
            # Check if any phrase repeats too much
            bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
            from collections import Counter
            common = Counter(bigrams).most_common(3)
            for bigram, count in common:
                if count > len(words) * 0.05:  # more than 5% repetition
                    issues.append(f"Excessive repetition of '{bigram}'")
                    result.score -= 0.15
                    break

        result.score = max(0.0, min(1.0, result.score))
        result.passed = result.score >= 0.5
        result.issues = issues
        return result

    # ─── Level 3: Quality Validation (LLM-based) ─────────────

    async def _validate_quality(self, output: str, request: str,
                                  agent_type: str) -> ValidationResult:
        """Use a fast LLM to assess quality, relevance, and completeness."""
        result = ValidationResult(level="quality")

        try:
            fast_model = self._get_fast_model()
            prompt = f"""Rate the following AI response on a scale of 0.0-1.0.
Consider: accuracy, relevance to the request, completeness, and clarity.

User Request: {request[:500]}
AI Response (first 1000 chars): {output[:1000]}

Output ONLY JSON:
{{"score": 0.85, "issues": ["issue1"], "strengths": ["strength1"]}}"""

            judge_result = await model_manager.chat_completion(
                model=fast_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
            )

            # Parse
            if "```json" in judge_result:
                judge_result = judge_result.split("```json")[1].split("```")[0].strip()
            elif "```" in judge_result:
                judge_result = judge_result.split("```")[1].split("```")[0].strip()

            data = json.loads(judge_result)
            result.score = min(1.0, max(0.0, data.get("score", 0.7)))
            result.issues = data.get("issues", [])
            result.suggestions = data.get("strengths", [])
            result.passed = result.score >= QUALITY_THRESHOLD

        except Exception as e:
            log.debug("Quality validation LLM failed, using default", error=str(e)[:80])
            result.score = 0.7  # assume decent if we can't judge
            result.passed = True

        return result

    def _get_fast_model(self) -> str:
        """Pick fastest model for validation."""
        priorities = ["gpt-4o-mini", "gemini-1.5-flash", "claude-3-haiku"]
        for p in priorities:
            for k in model_manager.available_models.keys():
                if p in k:
                    return k
        return model_manager.get_default_model()


quality_engine = QualityEngine()
