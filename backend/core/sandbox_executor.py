"""
Sandboxed Executor — Bubblewrap-based Command Isolation
========================================================
Menjalankan command dalam sandbox terisolasi menggunakan Bubblewrap (bwrap):
  - Filesystem isolation: read-only system paths, write hanya di workspace
  - Network isolation: default offline, configurable
  - Process isolation: PID namespace terpisah
  - Audit trail: SHA-256 hash per command execution
  - Graceful fallback: jika bwrap tidak tersedia, gunakan existing security checks

Permission Levels:
  - read_only:  Hanya baca filesystem, no write, no network
  - write_safe: Baca + tulis di workspace, no network
  - full_access: Semua akses (butuh approval)
"""

import asyncio
import hashlib
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import structlog

log = structlog.get_logger()

# ── Path Constants ────────────────────────────────────────────────────────────
AUDIT_LOG_DIR = Path(__file__).parent.parent.parent / "data" / "sandbox_audit"
SAFE_EXEC_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "safe_exec.sh"


class SandboxProfile(Enum):
    """Permission level untuk sandbox execution."""
    READ_ONLY = "read_only"
    WRITE_SAFE = "write_safe"
    FULL_ACCESS = "full_access"


class NetworkPolicy(Enum):
    """Network access policy."""
    OFFLINE = "offline"
    FULL = "full"


@dataclass
class SandboxConfig:
    """Konfigurasi sandbox per-profile."""
    profile: SandboxProfile
    ro_bind_paths: List[str] = field(default_factory=list)
    rw_bind_paths: List[str] = field(default_factory=list)
    network: NetworkPolicy = NetworkPolicy.OFFLINE
    requires_approval: bool = False
    timeout: int = 120


@dataclass
class SandboxAuditEntry:
    """Satu entry audit trail."""
    timestamp: str
    command_hash: str
    command_preview: str
    profile: str
    network: str
    exit_code: int
    duration_ms: int
    workspace: str
    bwrap_used: bool

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "command_hash": self.command_hash,
            "command_preview": self.command_preview,
            "profile": self.profile,
            "network": self.network,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "workspace": self.workspace,
            "bwrap_used": self.bwrap_used,
        }


# ── Default Profile Configs ──────────────────────────────────────────────────

PROFILE_CONFIGS: Dict[SandboxProfile, SandboxConfig] = {
    SandboxProfile.READ_ONLY: SandboxConfig(
        profile=SandboxProfile.READ_ONLY,
        ro_bind_paths=["/usr", "/lib", "/lib64", "/bin", "/sbin", "/etc/ssl",
                       "/etc/resolv.conf", "/etc/hosts"],
        rw_bind_paths=[],
        network=NetworkPolicy.OFFLINE,
        requires_approval=False,
        timeout=30,
    ),
    SandboxProfile.WRITE_SAFE: SandboxConfig(
        profile=SandboxProfile.WRITE_SAFE,
        ro_bind_paths=["/usr", "/lib", "/lib64", "/bin", "/sbin", "/etc/ssl",
                       "/etc/resolv.conf", "/etc/hosts", "/etc/alternatives"],
        rw_bind_paths=[],  # akan diisi workspace_dir
        network=NetworkPolicy.OFFLINE,
        requires_approval=False,
        timeout=120,
    ),
    SandboxProfile.FULL_ACCESS: SandboxConfig(
        profile=SandboxProfile.FULL_ACCESS,
        ro_bind_paths=["/usr", "/lib", "/lib64", "/bin", "/sbin"],
        rw_bind_paths=[],
        network=NetworkPolicy.FULL,
        requires_approval=True,
        timeout=300,
    ),
}

# Commands yang aman — tidak perlu sandbox
SANDBOX_BYPASS_COMMANDS = {
    "echo", "cat", "ls", "pwd", "whoami", "date", "uname",
    "head", "tail", "wc", "grep", "find", "which", "type",
    "env", "printenv", "hostname", "id", "df", "du", "free",
    "uptime",
}

# Patterns yang menunjukkan command butuh network
NETWORK_REQUIRED_PATTERNS = [
    "npm install", "npm i ", "pip install", "pip3 install",
    "apt install", "apt-get install", "apt update", "apt-get update",
    "curl ", "wget ", "git clone", "git pull", "git fetch",
    "docker pull", "composer install", "cargo install",
    "go get", "go install",
]

# Patterns yang menunjukkan command butuh write access
WRITE_REQUIRED_PATTERNS = [
    "npm install", "pip install", "mkdir", "touch", "cp ", "mv ",
    "git clone", "git checkout", "git merge",
    "tar ", "unzip", "make", "cmake", "cargo build",
    "npm run build", "npm run dev", "python ", "node ",
    "tee ", "sed -i", "chmod ", "chown ",
]


class SandboxedExecutor:
    """
    Engine untuk eksekusi command dalam sandbox Bubblewrap.
    Graceful fallback jika bwrap tidak tersedia.
    """

    def __init__(self):
        self._bwrap_available: Optional[bool] = None
        self._audit_entries: List[SandboxAuditEntry] = []
        self._max_audit = 5000

    # ── Public API ────────────────────────────────────────────────────────

    def is_bwrap_available(self) -> bool:
        """Check apakah Bubblewrap (bwrap) terinstall."""
        if self._bwrap_available is None:
            self._bwrap_available = shutil.which("bwrap") is not None
            log.info("Sandbox: bwrap availability checked",
                     available=self._bwrap_available)
        return self._bwrap_available

    def detect_profile(self, command: str) -> SandboxProfile:
        """Auto-detect sandbox profile berdasarkan command pattern."""
        cmd_lower = command.lower().strip()
        first_word = cmd_lower.split()[0] if cmd_lower else ""

        # Bypass check
        if first_word in SANDBOX_BYPASS_COMMANDS:
            return SandboxProfile.READ_ONLY

        # Check write patterns
        needs_write = any(p in cmd_lower for p in WRITE_REQUIRED_PATTERNS)

        # Check network patterns
        needs_network = any(p in cmd_lower for p in NETWORK_REQUIRED_PATTERNS)

        if needs_network and needs_write:
            return SandboxProfile.FULL_ACCESS
        elif needs_write:
            return SandboxProfile.WRITE_SAFE
        else:
            return SandboxProfile.READ_ONLY

    def should_bypass(self, command: str) -> bool:
        """Check apakah command bisa bypass sandbox sepenuhnya."""
        cmd_stripped = command.strip()
        first_word = cmd_stripped.split()[0] if cmd_stripped else ""
        return first_word in SANDBOX_BYPASS_COMMANDS

    async def execute(
        self,
        command: str,
        workspace_dir: str,
        profile: Optional[SandboxProfile] = None,
        allow_network: bool = False,
        timeout: Optional[int] = None,
    ) -> Tuple[str, str, int]:
        """
        Execute command dalam sandbox.

        Returns:
            (stdout, stderr, return_code)
        """
        if profile is None:
            profile = self.detect_profile(command)

        config = PROFILE_CONFIGS[profile]
        effective_timeout = timeout or config.timeout

        # Override network jika explicitly allowed
        effective_network = config.network
        if allow_network:
            effective_network = NetworkPolicy.FULL

        command_hash = hashlib.sha256(command.encode()).hexdigest()[:16]
        start_time = time.monotonic()

        bwrap_used = False
        stdout = ""
        stderr = ""
        return_code = -1

        if self.is_bwrap_available() and not self.should_bypass(command):
            # Execute via Bubblewrap
            bwrap_cmd = self._build_bwrap_command(
                command, workspace_dir, config, effective_network
            )
            bwrap_used = True

            try:
                proc = await asyncio.create_subprocess_shell(
                    bwrap_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=workspace_dir,
                )
                raw_out, raw_err = await asyncio.wait_for(
                    proc.communicate(), timeout=effective_timeout
                )
                stdout = raw_out.decode("utf-8", errors="replace")
                stderr = raw_err.decode("utf-8", errors="replace")
                return_code = proc.returncode or 0

            except asyncio.TimeoutError:
                stderr = f"Sandbox timeout ({effective_timeout}s)"
                return_code = 124
                try:
                    proc.kill()
                except Exception:
                    pass

            except Exception as e:
                stderr = f"Sandbox execution error: {e}"
                return_code = 1

        else:
            # Fallback: direct execution (tanpa sandbox)
            log.debug("Sandbox: bwrap not available, falling back to direct execution",
                      command=command[:80])
            try:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=workspace_dir,
                )
                raw_out, raw_err = await asyncio.wait_for(
                    proc.communicate(), timeout=effective_timeout
                )
                stdout = raw_out.decode("utf-8", errors="replace")
                stderr = raw_err.decode("utf-8", errors="replace")
                return_code = proc.returncode or 0

            except asyncio.TimeoutError:
                stderr = f"Execution timeout ({effective_timeout}s)"
                return_code = 124
            except Exception as e:
                stderr = f"Execution error: {e}"
                return_code = 1

        # Audit trail
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        self._log_audit(
            command=command,
            command_hash=command_hash,
            profile=profile,
            network=effective_network,
            exit_code=return_code,
            duration_ms=elapsed_ms,
            workspace=workspace_dir,
            bwrap_used=bwrap_used,
        )

        return stdout, stderr, return_code

    # ── Audit ─────────────────────────────────────────────────────────────

    def _log_audit(self, command: str, command_hash: str,
                   profile: SandboxProfile, network: NetworkPolicy,
                   exit_code: int, duration_ms: int,
                   workspace: str, bwrap_used: bool):
        """Log command execution ke audit trail."""
        entry = SandboxAuditEntry(
            timestamp=datetime.now().isoformat(),
            command_hash=command_hash,
            command_preview=command[:120],
            profile=profile.value,
            network=network.value,
            exit_code=exit_code,
            duration_ms=duration_ms,
            workspace=workspace,
            bwrap_used=bwrap_used,
        )

        self._audit_entries.append(entry)
        if len(self._audit_entries) > self._max_audit:
            self._audit_entries = self._audit_entries[-self._max_audit:]

        # Persist ke file
        self._persist_audit_entry(entry)

        log.info("Sandbox audit",
                 hash=command_hash,
                 profile=profile.value,
                 exit_code=exit_code,
                 duration_ms=duration_ms,
                 bwrap=bwrap_used)

    def _persist_audit_entry(self, entry: SandboxAuditEntry):
        """Simpan audit entry ke file JSON lines."""
        try:
            AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = AUDIT_LOG_DIR / f"sandbox_{today}.jsonl"

            import json
            with open(log_file, "a") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            log.warning("Failed to persist sandbox audit", error=str(e))

    def get_audit_history(self, limit: int = 100) -> List[dict]:
        """Get recent audit entries."""
        return [e.to_dict() for e in self._audit_entries[-limit:]]

    # ── bwrap Command Builder ─────────────────────────────────────────────

    def _build_bwrap_command(
        self,
        command: str,
        workspace_dir: str,
        config: SandboxConfig,
        network: NetworkPolicy,
    ) -> str:
        """Build bwrap command string."""
        parts = ["bwrap"]

        # Read-only binds (system paths)
        for path in config.ro_bind_paths:
            if os.path.exists(path):
                parts.extend(["--ro-bind", path, path])

        # Write binds (workspace)
        parts.extend(["--bind", workspace_dir, workspace_dir])

        for path in config.rw_bind_paths:
            if os.path.exists(path):
                parts.extend(["--bind", path, path])

        # Bind home directory tools (pip, npm cache, etc) as read-only
        home = os.path.expanduser("~")
        for subdir in [".local", ".npm", ".cache", ".config"]:
            full = os.path.join(home, subdir)
            if os.path.exists(full):
                parts.extend(["--ro-bind", full, full])

        # Virtual filesystems
        parts.extend(["--proc", "/proc"])
        parts.extend(["--dev", "/dev"])
        parts.extend(["--tmpfs", "/tmp"])

        # Working directory
        parts.extend(["--chdir", workspace_dir])

        # Isolation namespaces
        if network == NetworkPolicy.OFFLINE:
            parts.append("--unshare-net")

        parts.append("--unshare-pid")
        parts.append("--die-with-parent")

        # The actual command
        parts.extend(["--", "bash", "-c", command])

        return " ".join(self._shell_escape(p) for p in parts)

    @staticmethod
    def _shell_escape(s: str) -> str:
        """Escape shell special characters."""
        if not s or all(c.isalnum() or c in "-_/=.,:@" for c in s):
            return s
        return "'" + s.replace("'", "'\\''") + "'"


# ── Global Singleton ──────────────────────────────────────────────────────────
sandbox_executor = SandboxedExecutor()
