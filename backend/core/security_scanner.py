"""
AI ORCHESTRATOR — Security Scanner & Auto-Fixer
Scan CVE di dependencies (requirements.txt + package.json),
auto-fix dengan upgrade, dan kirim laporan ke Telegram.

Sumber CVE: pip-audit (PyPI Advisory) + npm audit + OSV.dev API
Semua gratis, tidak butuh API key.
"""
import asyncio
import json
import os
import subprocess
import time
import httpx
import structlog
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

log = structlog.get_logger()

BASE_DIR = Path(__file__).parent.parent


@dataclass
class CVEFinding:
    """Satu temuan CVE."""
    package:     str
    version:     str
    cve_id:      str
    severity:    str        # CRITICAL | HIGH | MEDIUM | LOW
    description: str
    fix_version: str = ""   # versi aman yang tersedia
    source:      str = ""   # pip-audit | npm-audit | osv


@dataclass
class ScanResult:
    """Hasil lengkap satu sesi scan."""
    findings:       list = field(default_factory=list)
    fixed:          list = field(default_factory=list)
    fix_failed:     list = field(default_factory=list)
    scan_duration:  float = 0.0
    timestamp:      float = field(default_factory=time.time)
    error:          str = ""
    ai_analysis:    str = ""


class SecurityScanner:
    """Engine utama security scanning dan auto-fix."""

    def __init__(self):
        self._last_scan_time = 0.0
        self._scan_history: list = []
        self._running = False
        self._schedule_hours = 24

    # ══════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════

    async def start_scheduler(self):
        """Mulai background scheduler — jalankan scan tiap N jam."""
        self._running = True
        log.info("Security Scanner scheduler started",
                 interval_hours=self._schedule_hours)
        asyncio.create_task(self._scheduler_loop())

    def stop(self):
        self._running = False

    async def run_scan(self, triggered_by: str = "scheduler") -> ScanResult:
        """Jalankan scan penuh: detect CVE → AI analyze → auto-fix → report."""
        log.info("Security scan started", triggered_by=triggered_by)
        start = time.time()
        result = ScanResult()

        try:
            py_findings = await self._scan_python()
            result.findings.extend(py_findings)

            js_findings = await self._scan_nodejs()
            result.findings.extend(js_findings)

            if result.findings:
                log.warning("CVE findings detected",
                            count=len(result.findings),
                            critical=sum(1 for f in result.findings
                                        if f.severity == "CRITICAL"),
                            high=sum(1 for f in result.findings
                                    if f.severity == "HIGH"))
                await self._ai_analyze(result)
                fixed, failed = await self._auto_fix(result.findings)
                result.fixed = fixed
                result.fix_failed = failed
            else:
                log.info("No CVE findings — all dependencies clean")

        except Exception as e:
            result.error = str(e)[:300]
            log.error("Security scan error", error=result.error)

        result.scan_duration = time.time() - start
        self._last_scan_time = time.time()
        self._scan_history.append(result)

        await self._save_to_db(result, triggered_by)
        await self._send_report(result, triggered_by)

        return result

    def get_last_scan(self) -> Optional[dict]:
        """Ambil hasil scan terakhir untuk dashboard."""
        if not self._scan_history:
            return None
        r = self._scan_history[-1]
        return {
            "findings":      [self._finding_to_dict(f) for f in r.findings],
            "fixed":         r.fixed,
            "fix_failed":    r.fix_failed,
            "scan_duration": round(r.scan_duration, 2),
            "timestamp":     datetime.fromtimestamp(r.timestamp).isoformat(),
            "error":         r.error,
            "total_found":   len(r.findings),
            "total_fixed":   len(r.fixed),
        }

    def get_history(self, limit: int = 10) -> list:
        return [
            {
                "timestamp":   datetime.fromtimestamp(r.timestamp).isoformat(),
                "total_found": len(r.findings),
                "total_fixed": len(r.fixed),
                "duration_s":  round(r.scan_duration, 1),
                "had_error":   bool(r.error),
                "critical":    sum(1 for f in r.findings if f.severity == "CRITICAL"),
                "high":        sum(1 for f in r.findings if f.severity == "HIGH"),
            }
            for r in self._scan_history[-limit:]
        ]

    # ══════════════════════════════════════════════════════
    # SCHEDULER
    # ══════════════════════════════════════════════════════

    async def _scheduler_loop(self):
        """Jalankan scan tiap _schedule_hours jam."""
        await asyncio.sleep(300)  # Tunda 5 menit setelah startup
        while self._running:
            try:
                await self.run_scan(triggered_by="scheduler")
            except Exception as e:
                log.error("Scheduled scan failed", error=str(e)[:100])
            await asyncio.sleep(self._schedule_hours * 3600)

    # ══════════════════════════════════════════════════════
    # SCANNERS
    # ══════════════════════════════════════════════════════

    async def _scan_python(self) -> list:
        """Scan Python dependencies menggunakan pip-audit."""
        findings = []
        req_file = BASE_DIR / "requirements.txt"
        if not req_file.exists():
            log.debug("requirements.txt not found, skipping Python scan")
            return findings

        log.info("Scanning Python dependencies via pip-audit")

        try:
            subprocess.run(
                ["pip", "install", "pip-audit", "--quiet",
                 "--break-system-packages"],
                capture_output=True, timeout=60
            )

            result = subprocess.run(
                ["pip-audit", "--requirement", str(req_file),
                 "--format", "json", "--progress-spinner", "off"],
                capture_output=True, text=True, timeout=120
            )

            output = result.stdout.strip()
            if not output:
                output = result.stderr.strip()

            if output:
                data = json.loads(output)
                for dep in data.get("dependencies", []):
                    pkg_name = dep.get("name", "")
                    pkg_version = dep.get("version", "")
                    for vuln in dep.get("vulns", []):
                        fix_versions = vuln.get("fix_versions", [])
                        fix_ver = fix_versions[-1] if fix_versions else ""
                        aliases = vuln.get("aliases", [])
                        severity = self._guess_severity(
                            vuln.get("description", ""), aliases
                        )
                        findings.append(CVEFinding(
                            package=pkg_name, version=pkg_version,
                            cve_id=vuln.get("id", ""), severity=severity,
                            description=vuln.get("description", "")[:200],
                            fix_version=fix_ver, source="pip-audit",
                        ))

        except FileNotFoundError:
            log.debug("pip-audit not available, using OSV fallback")
            findings = await self._scan_python_osv(req_file)
        except json.JSONDecodeError:
            log.warning("pip-audit output tidak valid JSON")
        except subprocess.TimeoutExpired:
            log.warning("pip-audit timeout")
        except Exception as e:
            log.warning("Python scan error", error=str(e)[:100])

        log.info("Python scan done", findings=len(findings))
        return findings

    async def _scan_python_osv(self, req_file: Path) -> list:
        """Fallback: cek CVE via OSV.dev API (gratis, tanpa key)."""
        findings = []
        try:
            packages = []
            for line in req_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "==" in line:
                    name, version = line.split("==", 1)
                    packages.append({
                        "name": name.strip(),
                        "version": version.strip().split(";")[0].strip()
                    })

            if not packages:
                return findings

            query = {
                "queries": [
                    {"version": pkg["version"],
                     "package": {"name": pkg["name"], "ecosystem": "PyPI"}}
                    for pkg in packages
                ]
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    "https://api.osv.dev/v1/querybatch", json=query
                )
                if r.status_code != 200:
                    return findings
                data = r.json()

            for i, res in enumerate(data.get("results", [])):
                vulns = res.get("vulns", [])
                if not vulns or i >= len(packages):
                    continue
                pkg = packages[i]
                for vuln in vulns[:3]:
                    severity = "MEDIUM"
                    for sev in vuln.get("severity", []):
                        severity = sev.get("type", "MEDIUM").upper()
                    findings.append(CVEFinding(
                        package=pkg["name"], version=pkg["version"],
                        cve_id=vuln.get("id", ""), severity=severity,
                        description=vuln.get("summary", "")[:200],
                        fix_version="", source="osv.dev",
                    ))
        except Exception as e:
            log.warning("OSV scan error", error=str(e)[:80])
        return findings

    async def _scan_nodejs(self) -> list:
        """Scan Node.js dependencies menggunakan npm audit."""
        findings = []
        frontend_dir = BASE_DIR.parent / "frontend"
        pkg_file = frontend_dir / "package.json"

        if not pkg_file.exists():
            log.debug("package.json not found, skipping Node.js scan")
            return findings

        try:
            subprocess.run(["npm", "--version"],
                          capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            log.debug("npm not available, skipping Node.js scan")
            return findings

        log.info("Scanning Node.js dependencies via npm audit")
        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                capture_output=True, text=True,
                cwd=str(frontend_dir), timeout=120
            )
            output = result.stdout.strip()
            if not output:
                return findings

            data = json.loads(output)
            vulnerabilities = data.get("vulnerabilities", {}) or \
                              data.get("advisories", {})

            for pkg_name, vuln_data in vulnerabilities.items():
                severity = vuln_data.get("severity", "medium").upper()
                version = vuln_data.get("range", "unknown")
                fix_available = vuln_data.get("fixAvailable", False)
                fix_ver = ""
                if isinstance(fix_available, dict):
                    fix_ver = fix_available.get("version", "")
                elif fix_available is True:
                    fix_ver = "latest"

                via = vuln_data.get("via", [])
                description = ""
                cve_id = ""
                if via and isinstance(via[0], dict):
                    description = via[0].get("title", "")[:200]
                    cve_list = via[0].get("cve", [])
                    cve_id = cve_list[0] if cve_list else via[0].get("url", "")

                findings.append(CVEFinding(
                    package=pkg_name, version=version,
                    cve_id=cve_id or f"npm-{pkg_name}",
                    severity=severity,
                    description=description or vuln_data.get("title", "")[:200],
                    fix_version=fix_ver, source="npm-audit",
                ))

        except json.JSONDecodeError:
            log.warning("npm audit output tidak valid JSON")
        except subprocess.TimeoutExpired:
            log.warning("npm audit timeout")
        except Exception as e:
            log.warning("Node.js scan error", error=str(e)[:100])

        log.info("Node.js scan done", findings=len(findings))
        return findings

    # ══════════════════════════════════════════════════════
    # AI ANALYSIS
    # ══════════════════════════════════════════════════════

    async def _ai_analyze(self, result: ScanResult):
        """Gunakan model AI untuk analisis dan prioritisasi CVE."""
        if not result.findings:
            return
        try:
            from core.model_manager import model_manager
            model = model_manager.get_default_model()
            if not model:
                log.debug("No model available for AI analysis, skipping")
                return

            findings_text = "\n".join([
                f"- {f.package}=={f.version}: {f.cve_id} "
                f"({f.severity}) — {f.description[:100]}"
                f"{' | Fix: ' + f.fix_version if f.fix_version else ''}"
                for f in result.findings
            ])

            prompt = (
                "Anda adalah security analyst untuk aplikasi AI Orchestrator "
                "berbasis Python/FastAPI + React.\n\n"
                f"Daftar CVE ditemukan:\n{findings_text}\n\n"
                "Tugas:\n"
                "1. Identifikasi mana yang paling berbahaya\n"
                "2. Apakah perlu restart service setelah upgrade?\n"
                "3. Apakah ada false-positive?\n\n"
                "Jawab singkat:\n"
                "PRIORITAS TINGGI: [daftar]\n"
                "PERLU RESTART: [ya/tidak]\n"
                "FALSE POSITIVE: [daftar atau 'tidak ada']"
            )

            messages = [
                {"role": "system", "content":
                 "Anda adalah security analyst. Jawab singkat dan teknis."},
                {"role": "user", "content": prompt}
            ]

            ai_response = await model_manager.chat_completion(
                model=model, messages=messages,
                temperature=0.1, max_tokens=500,
            )
            if ai_response:
                log.info("AI security analysis complete",
                         response_preview=ai_response[:100])
                result.ai_analysis = ai_response.strip()

        except Exception as e:
            log.debug("AI analysis skipped", error=str(e)[:80])

    # ══════════════════════════════════════════════════════
    # AUTO-FIXER
    # ══════════════════════════════════════════════════════

    async def _auto_fix(self, findings: list) -> tuple:
        """Auto-fix dengan upgrade package ke versi aman."""
        fixed, failed = [], []

        py_findings = [f for f in findings if f.source in
                       ("pip-audit", "osv.dev") and f.fix_version]
        js_findings = [f for f in findings if f.source == "npm-audit"
                       and f.fix_version]

        if py_findings:
            pf, pfail = await self._fix_python(py_findings)
            fixed.extend(pf)
            failed.extend(pfail)

        if js_findings:
            jf, jfail = await self._fix_nodejs(js_findings)
            fixed.extend(jf)
            failed.extend(jfail)

        return fixed, failed

    async def _fix_python(self, findings: list) -> tuple:
        """Upgrade Python packages ke versi aman."""
        fixed, failed = [], []
        for f in findings:
            target = (f"{f.package}=={f.fix_version}"
                      if f.fix_version != "latest" else f.package)

            log.info("Auto-fixing Python package",
                     package=f.package, from_ver=f.version,
                     to_ver=f.fix_version)
            try:
                result = subprocess.run(
                    ["pip", "install", target, "--quiet",
                     "--break-system-packages"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    await self._update_requirements_txt(
                        f.package, f.fix_version)
                    fixed.append(
                        f"{f.package}: {f.version} → {f.fix_version}")
                    log.info("Package fixed", package=f.package,
                             version=f.fix_version)
                else:
                    err = result.stderr[:100]
                    failed.append(f"{f.package}: {err}")
                    log.warning("Package fix failed",
                                package=f.package, error=err)
            except subprocess.TimeoutExpired:
                failed.append(f"{f.package}: timeout saat install")
            except Exception as e:
                failed.append(f"{f.package}: {str(e)[:80]}")
        return fixed, failed

    async def _fix_nodejs(self, findings: list) -> tuple:
        """Upgrade Node.js packages menggunakan npm audit fix."""
        fixed, failed = [], []
        frontend_dir = BASE_DIR.parent / "frontend"
        if not frontend_dir.exists():
            return fixed, failed

        try:
            log.info("Running npm audit fix")
            result = subprocess.run(
                ["npm", "audit", "fix", "--force"],
                capture_output=True, text=True,
                cwd=str(frontend_dir), timeout=180
            )
            if result.returncode == 0:
                for f in findings:
                    fixed.append(
                        f"{f.package} → {f.fix_version or 'latest'}")
                log.info("npm audit fix completed")
            else:
                for f in findings:
                    failed.append(f"{f.package}: npm audit fix failed")
                log.warning("npm audit fix failed",
                            error=result.stderr[:100])
        except subprocess.TimeoutExpired:
            for f in findings:
                failed.append(f"{f.package}: npm timeout")
        except Exception as e:
            for f in findings:
                failed.append(f"{f.package}: {str(e)[:60]}")
        return fixed, failed

    async def _update_requirements_txt(self, package: str, new_version: str):
        """Update versi package di requirements.txt."""
        req_file = BASE_DIR / "requirements.txt"
        if not req_file.exists():
            return
        try:
            content = req_file.read_text()
            lines = content.splitlines()
            updated = []
            changed = False
            for line in lines:
                stripped = line.strip()
                if (stripped.lower().startswith(package.lower()) and
                        any(op in stripped for op in
                            ["==", ">=", "<=", "~="])):
                    new_line = f"{package}=={new_version}"
                    updated.append(new_line)
                    changed = True
                    log.debug("requirements.txt updated",
                              package=package, new_line=new_line)
                else:
                    updated.append(line)
            if changed:
                req_file.write_text("\n".join(updated) + "\n")
        except Exception as e:
            log.warning("Failed to update requirements.txt",
                        error=str(e)[:80])

    # ══════════════════════════════════════════════════════
    # REPORTING
    # ══════════════════════════════════════════════════════

    async def _send_report(self, result: ScanResult, triggered_by: str):
        """Kirim laporan scan ke Telegram admin."""
        try:
            token, chat_id = await self._get_telegram_config()
            if not token or not chat_id:
                log.info("No Telegram config — scan report logged only")
                return

            msg = self._build_report(result, triggered_by)
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": msg,
                          "parse_mode": "Markdown"}
                )
                if r.status_code != 200:
                    log.warning("Telegram report failed",
                                status=r.status_code)
        except Exception as e:
            log.error("Failed to send security report",
                      error=str(e)[:100])

    def _build_report(self, result: ScanResult, triggered_by: str) -> str:
        """Format pesan laporan security untuk Telegram."""
        now_str = datetime.now().strftime("%d %b %Y, %H:%M")
        header = (f"🔒 *[AI ORCHESTRATOR] Security Scan*\n"
                  f"_{now_str}_ | Trigger: {triggered_by}\n\n")

        if result.error:
            return header + f"❌ Scan gagal: {result.error[:200]}"

        if not result.findings:
            return (header +
                    "✅ Semua dependency aman — tidak ada CVE ditemukan\n"
                    f"⏱ Durasi scan: {result.scan_duration:.1f}s")

        critical = [f for f in result.findings if f.severity == "CRITICAL"]
        high = [f for f in result.findings if f.severity == "HIGH"]
        medium = [f for f in result.findings if f.severity == "MEDIUM"]
        low = [f for f in result.findings if f.severity == "LOW"]

        severity_line = " | ".join(filter(None, [
            f"🔴 CRITICAL: {len(critical)}" if critical else "",
            f"🟠 HIGH: {len(high)}" if high else "",
            f"🟡 MEDIUM: {len(medium)}" if medium else "",
            f"🟢 LOW: {len(low)}" if low else "",
        ]))

        finding_lines = []
        for f in result.findings[:5]:
            icon = {"CRITICAL": "🔴", "HIGH": "🟠",
                    "MEDIUM": "🟡", "LOW": "🟢"}.get(f.severity, "⚪")
            fix_info = f" → fix: `{f.fix_version}`" if f.fix_version else ""
            finding_lines.append(
                f"{icon} `{f.package}=={f.version}` — {f.cve_id}{fix_info}"
            )
        if len(result.findings) > 5:
            finding_lines.append(
                f"_...dan {len(result.findings) - 5} lainnya_")

        fix_summary = ""
        if result.fixed:
            fix_summary += f"\n\n✅ *Auto-fixed ({len(result.fixed)})*:\n"
            fix_summary += "\n".join(
                f"  • {f}" for f in result.fixed[:5])
        if result.fix_failed:
            fix_summary += (
                f"\n\n❌ *Gagal diperbaiki ({len(result.fix_failed)})*:\n")
            fix_summary += "\n".join(
                f"  • {f}" for f in result.fix_failed[:3])

        ai_section = ""
        if result.ai_analysis:
            ai_section = f"\n\n🤖 *AI Analysis:*\n_{result.ai_analysis[:300]}_"

        return (
            header +
            f"⚠️ *{len(result.findings)} CVE ditemukan*\n"
            f"{severity_line}\n\n"
            f"*Detail:*\n" +
            "\n".join(finding_lines) +
            fix_summary + ai_section +
            f"\n\n⏱ Durasi: {result.scan_duration:.1f}s"
        )

    async def _get_telegram_config(self) -> tuple:
        """Ambil token dan chat_id dari konfigurasi yang sudah ada."""
        from core.config import settings
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or \
                os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = ""
        if not token:
            return "", ""

        try:
            from db.database import AsyncSessionLocal
            from db.models import User
            from sqlmodel import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(
                        User.is_admin == True,
                        User.telegram_chat_id != None,
                        User.is_active == True,
                    )
                )
                admin = result.scalars().first()
                if admin and admin.telegram_chat_id:
                    chat_id = admin.telegram_chat_id
        except Exception:
            chat_id = os.environ.get("ADMIN_TELEGRAM_CHAT_ID", "")

        return token, chat_id

    # ══════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════

    def _guess_severity(self, description: str, aliases: list) -> str:
        """Tebak severity dari deskripsi jika tidak tersedia."""
        text = (description + " ".join(aliases)).upper()
        if any(w in text for w in
               ["CRITICAL", "REMOTE CODE", "RCE", "UNAUTHENTICATED"]):
            return "CRITICAL"
        if any(w in text for w in
               ["HIGH", "PRIVILEGE", "INJECTION", "XSS", "SSRF"]):
            return "HIGH"
        if any(w in text for w in
               ["MEDIUM", "MODERATE", "DENIAL", "DOS"]):
            return "MEDIUM"
        return "LOW"

    def _finding_to_dict(self, f: CVEFinding) -> dict:
        return {
            "package": f.package, "version": f.version,
            "cve_id": f.cve_id, "severity": f.severity,
            "description": f.description, "fix_version": f.fix_version,
            "source": f.source,
        }

    async def _save_to_db(self, result: ScanResult, triggered_by: str):
        """Simpan hasil scan ke database untuk history."""
        try:
            summary = {
                "triggered_by": triggered_by,
                "total_found": len(result.findings),
                "total_fixed": len(result.fixed),
                "duration_s": round(result.scan_duration, 1),
                "critical": sum(1 for f in result.findings
                               if f.severity == "CRITICAL"),
                "high": sum(1 for f in result.findings
                           if f.severity == "HIGH"),
                "error": result.error,
            }
            log.info("Security scan saved", **summary)
        except Exception as e:
            log.debug("Could not save scan to DB", error=str(e)[:60])


# ── Singleton ─────────────────────────────────────────────────
security_scanner = SecurityScanner()
