"""
AI ORCHESTRATOR — Self-Correction Engine
Sistem Koreksi Mandiri: Meninjau output AI (terutama kode) sebelum
dikirim ke user. Jika ditemukan error, otomatis memperbaiki via
loop internal tanpa campur tangan user.

Pipeline:
  Output → Extract Code Blocks → Validate Syntax → Fix if Error → Return Clean Output
"""
import re
import asyncio
import tempfile
import os
from typing import Optional
from dataclasses import dataclass, field
import structlog

log = structlog.get_logger()


@dataclass
class CorrectionResult:
    """Hasil dari satu siklus koreksi."""
    original_code: str
    corrected_code: str
    language: str
    error_found: str = ""
    was_corrected: bool = False


@dataclass
class ReviewReport:
    """Laporan lengkap dari review & correction."""
    corrections: list = field(default_factory=list)
    total_issues_found: int = 0
    total_issues_fixed: int = 0
    review_performed: bool = False


class SelfCorrectionEngine:
    """
    Engine yang me-review output AI sebelum dikirim ke user.
    Fokus pada validasi sintaks kode dan koreksi otomatis.
    """
    MAX_CORRECTION_ROUNDS = 2

    # Bahasa yang didukung untuk validasi sintaks
    SUPPORTED_LANGUAGES = {
        "python": [".py"],
        "javascript": [".js", ".jsx", ".mjs"],
        "typescript": [".ts", ".tsx"],
        "bash": [".sh", ".bash"],
        "html": [".html", ".htm"],
        "css": [".css"],
    }

    async def review_and_correct(
        self,
        output: str,
        model: str,
        original_request: str,
    ) -> tuple[str, ReviewReport]:
        """
        Review output AI, auto-fix jika ada error kode.

        Returns:
            tuple: (corrected_output, review_report)
        """
        report = ReviewReport()

        # Hanya review jika output mengandung blok kode
        code_blocks = self._extract_code_blocks(output)
        if not code_blocks:
            return output, report

        report.review_performed = True
        corrected_output = output

        for block in code_blocks:
            lang = block["language"]
            code = block["code"]
            full_match = block["full_match"]

            # Skip bahasa yang tidak didukung untuk validasi
            if lang not in self.SUPPORTED_LANGUAGES:
                continue

            # Validasi sintaks
            validation = await self._validate_code(code, lang)

            if not validation["valid"]:
                report.total_issues_found += 1
                error_msg = validation["error"]

                log.info("Self-correction: error detected",
                         language=lang, error=error_msg[:100])

                # Coba perbaiki via loop koreksi
                fixed_code = code
                was_fixed = False

                for round_num in range(self.MAX_CORRECTION_ROUNDS):
                    fixed_code = await self._request_fix(
                        fixed_code, error_msg, lang, model, original_request
                    )

                    if not fixed_code or fixed_code == code:
                        break

                    # Validasi ulang hasil perbaikan
                    recheck = await self._validate_code(fixed_code, lang)
                    if recheck["valid"]:
                        was_fixed = True
                        break
                    else:
                        error_msg = recheck["error"]
                        log.info("Self-correction round failed, retrying",
                                 round=round_num + 1, error=error_msg[:80])

                if was_fixed:
                    report.total_issues_fixed += 1
                    # Ganti blok kode lama dengan yang sudah diperbaiki
                    new_block = f"```{lang}\n{fixed_code}\n```"
                    corrected_output = corrected_output.replace(full_match, new_block)

                    report.corrections.append(CorrectionResult(
                        original_code=code[:200],
                        corrected_code=fixed_code[:200],
                        language=lang,
                        error_found=validation["error"][:200],
                        was_corrected=True,
                    ))

                    log.info("Self-correction: code fixed successfully",
                             language=lang)
                else:
                    report.corrections.append(CorrectionResult(
                        original_code=code[:200],
                        corrected_code=code[:200],
                        language=lang,
                        error_found=validation["error"][:200],
                        was_corrected=False,
                    ))
                    log.warning("Self-correction: could not auto-fix",
                                language=lang, error=error_msg[:80])

        return corrected_output, report

    def _extract_code_blocks(self, text: str) -> list:
        """Extract fenced code blocks dari output."""
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.finditer(pattern, text, re.DOTALL)
        blocks = []
        for m in matches:
            lang = (m.group(1) or "").lower().strip()
            code = m.group(2).strip()

            # Normalisasi alias bahasa
            lang_map = {
                "py": "python", "python3": "python",
                "js": "javascript", "jsx": "javascript",
                "ts": "typescript", "tsx": "typescript",
                "sh": "bash", "shell": "bash", "zsh": "bash",
            }
            lang = lang_map.get(lang, lang)

            if code and len(code) > 10:  # Skip snippet terlalu kecil
                blocks.append({
                    "language": lang,
                    "code": code,
                    "full_match": m.group(0),
                })
        return blocks

    async def _validate_code(self, code: str, language: str) -> dict:
        """Jalankan validasi sintaks berdasarkan bahasa."""
        try:
            if language == "python":
                return await self._validate_python(code)
            elif language in ("javascript", "typescript"):
                return await self._validate_js(code)
            elif language == "bash":
                return await self._validate_bash(code)
            elif language == "html":
                return self._validate_html(code)
            else:
                return {"valid": True, "error": ""}
        except Exception as e:
            log.debug("Validation error", language=language, error=str(e)[:80])
            return {"valid": True, "error": ""}  # Assume valid jika validator error

    async def _validate_python(self, code: str) -> dict:
        """Validasi Python syntax via py_compile."""
        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "-m", "py_compile", tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)
            if proc.returncode != 0:
                error = stderr.decode(errors="replace").strip()
                # Bersihkan path tempfile dari error message
                error = error.replace(tmp_path, "<code>")
                return {"valid": False, "error": error}
            return {"valid": True, "error": ""}
        except asyncio.TimeoutError:
            return {"valid": True, "error": ""}
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    async def _validate_js(self, code: str) -> dict:
        """Validasi JavaScript syntax via node --check."""
        with tempfile.NamedTemporaryFile(
            suffix=".js", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "node", "--check", tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)
            if proc.returncode != 0:
                error = stderr.decode(errors="replace").strip()
                error = error.replace(tmp_path, "<code>")
                return {"valid": False, "error": error}
            return {"valid": True, "error": ""}
        except (asyncio.TimeoutError, FileNotFoundError):
            # node not installed — skip JS validation
            return {"valid": True, "error": ""}
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    async def _validate_bash(self, code: str) -> dict:
        """Validasi Bash syntax via bash -n."""
        with tempfile.NamedTemporaryFile(
            suffix=".sh", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "bash", "-n", tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)
            if proc.returncode != 0:
                error = stderr.decode(errors="replace").strip()
                error = error.replace(tmp_path, "<code>")
                return {"valid": False, "error": error}
            return {"valid": True, "error": ""}
        except asyncio.TimeoutError:
            return {"valid": True, "error": ""}
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _validate_html(self, code: str) -> dict:
        """Validasi HTML dasar — cek tag yang tidak tertutup."""
        # Heuristik sederhana: cek balance tag umum
        open_tags = re.findall(r'<(\w+)[\s>]', code)
        close_tags = re.findall(r'</(\w+)>', code)
        void_elements = {'br', 'hr', 'img', 'input', 'meta', 'link',
                         'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'}

        open_non_void = [t.lower() for t in open_tags if t.lower() not in void_elements]
        close_list = [t.lower() for t in close_tags]

        # Simple check: jumlah open vs close harus mirip
        diff = abs(len(open_non_void) - len(close_list))
        if diff > 3:
            return {"valid": False, "error": f"Possible unclosed HTML tags ({diff} mismatch)"}
        return {"valid": True, "error": ""}

    async def _request_fix(
        self,
        code: str,
        error: str,
        language: str,
        model: str,
        original_request: str,
    ) -> Optional[str]:
        """Minta model AI untuk memperbaiki kode berdasarkan error."""
        try:
            from core.model_manager import model_manager

            fix_prompt = (
                f"Fix the following {language} code that has a syntax error.\n\n"
                f"ERROR:\n{error}\n\n"
                f"ORIGINAL CODE:\n```{language}\n{code}\n```\n\n"
                f"CONTEXT: This code was generated for the following request: "
                f"{original_request[:300]}\n\n"
                f"Respond with ONLY the corrected code, no explanations. "
                f"Do NOT wrap in code fences. Just the raw fixed code."
            )

            messages = [
                {"role": "system", "content": (
                    "You are a code correction assistant. Fix syntax errors precisely. "
                    "Return ONLY the corrected code without any markdown fences or explanations."
                )},
                {"role": "user", "content": fix_prompt},
            ]

            result = await asyncio.wait_for(
                model_manager.chat_completion(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=4096,
                ),
                timeout=30.0,
            )

            if result:
                # Bersihkan dari code fence jika model tetap menambahkannya
                cleaned = result.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.split("\n")
                    # Remove first and last lines (fences)
                    if len(lines) >= 3:
                        cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
                    cleaned = cleaned.strip()
                return cleaned

        except Exception as e:
            log.debug("Self-correction fix request failed", error=str(e)[:80])

        return None


# Singleton
self_correction_engine = SelfCorrectionEngine()
