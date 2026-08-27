"""
System Tools — Comprehensive Server/PC Management for AI Orchestrator
=====================================================================
Tools untuk mengoperasikan dan mengelola server/PC secara otonom:

  system_info      — Informasi sistem lengkap (OS, CPU, RAM, Disk, Network)
  process_manager  — Kelola proses: list, find, kill, ports, services
"""

import os
import asyncio
import platform
import shutil
from datetime import datetime
from typing import Optional
import structlog

log = structlog.get_logger()

# ── Safety: PID yang tidak boleh di-kill ─────────────────────────────────────
_PROTECTED_PIDS = {1}  # init/systemd
_PROTECTED_PROCESS_NAMES = {
    "systemd", "sshd", "init", "kthreadd", "ksoftirqd",
    "migration", "rcu_", "watchdog",
}


def _format_bytes(size_bytes: int) -> str:
    """Format bytes ke human-readable."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024**2:.1f} MB"
    else:
        return f"{size_bytes / 1024**3:.2f} GB"


async def _run_cmd(cmd: str, timeout: float = 10.0) -> str:
    """Jalankan command dan kembalikan stdout."""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode("utf-8", errors="replace").strip()
    except asyncio.TimeoutError:
        return "(timeout)"
    except Exception as e:
        return f"(error: {e})"


# ── 1. system_info ───────────────────────────────────────────────────────────

async def system_info(category: str = "all") -> str:
    """
    Kumpulkan informasi sistem server secara komprehensif.

    Args:
        category: 'all', 'cpu', 'memory', 'disk', 'network', 'processes', 'os'

    Returns:
        Informasi sistem terstruktur dan mudah dibaca
    """
    try:
        sections = []
        cat = category.lower().strip()

        # ── OS Info ──────────────────────────────────────────────────────
        if cat in ("all", "os"):
            uname = platform.uname()
            uptime = await _run_cmd("uptime -p 2>/dev/null || uptime")
            hostname = await _run_cmd("hostname")
            kernel = await _run_cmd("uname -r")
            distro = await _run_cmd("cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'\"' -f2")
            if not distro:
                distro = f"{uname.system} {uname.release}"
            
            current_user = await _run_cmd("whoami")
            shell = os.environ.get("SHELL", "unknown")

            sections.append(
                f"🖥️  SISTEM OPERASI\n"
                f"{'─' * 50}\n"
                f"  Hostname     : {hostname}\n"
                f"  OS           : {distro}\n"
                f"  Kernel       : {kernel}\n"
                f"  Arsitektur   : {uname.machine}\n"
                f"  User         : {current_user}\n"
                f"  Shell        : {shell}\n"
                f"  Uptime       : {uptime}\n"
                f"  Python       : {platform.python_version()}"
            )

        # ── CPU Info ─────────────────────────────────────────────────────
        if cat in ("all", "cpu"):
            cpu_count = os.cpu_count() or 0
            cpu_model = await _run_cmd("grep 'model name' /proc/cpuinfo 2>/dev/null | head -1 | cut -d':' -f2")
            cpu_model = cpu_model.strip() if cpu_model else "Unknown"
            load_avg = await _run_cmd("cat /proc/loadavg 2>/dev/null")
            cpu_usage = await _run_cmd("top -bn1 2>/dev/null | grep 'Cpu(s)' | head -1")

            load_parts = load_avg.split() if load_avg else []
            load_str = f"{load_parts[0]}, {load_parts[1]}, {load_parts[2]}" if len(load_parts) >= 3 else load_avg

            sections.append(
                f"\n⚡ CPU\n"
                f"{'─' * 50}\n"
                f"  Model        : {cpu_model}\n"
                f"  Core/Thread  : {cpu_count}\n"
                f"  Load Avg     : {load_str}\n"
                f"  Usage        : {cpu_usage.strip() if cpu_usage else 'N/A'}"
            )

        # ── Memory Info ──────────────────────────────────────────────────
        if cat in ("all", "memory"):
            mem_info = await _run_cmd("free -b 2>/dev/null")
            if mem_info:
                lines = mem_info.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 7:
                        total = int(parts[1])
                        used = int(parts[2])
                        free = int(parts[3])
                        available = int(parts[6]) if len(parts) > 6 else free
                        pct_used = (used / total * 100) if total > 0 else 0

                        # Bar visual
                        bar_len = 30
                        filled = int(bar_len * pct_used / 100)
                        bar = "█" * filled + "░" * (bar_len - filled)

                        sections.append(
                            f"\n💾 MEMORY (RAM)\n"
                            f"{'─' * 50}\n"
                            f"  Total        : {_format_bytes(total)}\n"
                            f"  Used         : {_format_bytes(used)} ({pct_used:.1f}%)\n"
                            f"  Available    : {_format_bytes(available)}\n"
                            f"  [{bar}] {pct_used:.1f}%"
                        )

                # Swap
                if len(lines) >= 3:
                    swap_parts = lines[2].split()
                    if len(swap_parts) >= 3:
                        swap_total = int(swap_parts[1])
                        swap_used = int(swap_parts[2])
                        if swap_total > 0:
                            sections.append(
                                f"  Swap Total   : {_format_bytes(swap_total)}\n"
                                f"  Swap Used    : {_format_bytes(swap_used)}"
                            )

        # ── Disk Info ────────────────────────────────────────────────────
        if cat in ("all", "disk"):
            disk_info = await _run_cmd("df -h --output=target,size,used,avail,pcent 2>/dev/null | head -15")
            if not disk_info:
                disk_info = await _run_cmd("df -h | head -15")

            sections.append(
                f"\n💿 DISK\n"
                f"{'─' * 50}\n"
                f"{disk_info}"
            )

            # Disk I/O (if available)
            disk_io = await _run_cmd("iostat -d 2>/dev/null | head -10")
            if disk_io and "error" not in disk_io.lower():
                sections.append(f"\n  I/O Stats:\n{disk_io}")

        # ── Network Info ─────────────────────────────────────────────────
        if cat in ("all", "network"):
            ip_info = await _run_cmd("ip -4 addr show 2>/dev/null | grep inet | grep -v 127.0.0.1 | awk '{print $NF\": \"$2}'")
            if not ip_info:
                ip_info = await _run_cmd("hostname -I 2>/dev/null")

            dns = await _run_cmd("cat /etc/resolv.conf 2>/dev/null | grep nameserver | head -3")
            gateway = await _run_cmd("ip route 2>/dev/null | grep default | head -1 | awk '{print $3}'")

            connections = await _run_cmd("ss -tuln 2>/dev/null | grep LISTEN | wc -l")

            sections.append(
                f"\n🌐 NETWORK\n"
                f"{'─' * 50}\n"
                f"  IP Addresses :\n    {ip_info.replace(chr(10), chr(10) + '    ') if ip_info else 'N/A'}\n"
                f"  Gateway      : {gateway or 'N/A'}\n"
                f"  DNS          : {dns.replace('nameserver ', '').replace(chr(10), ', ') if dns else 'N/A'}\n"
                f"  Listening    : {connections} ports"
            )

        # ── Top Processes ────────────────────────────────────────────────
        if cat in ("all", "processes"):
            top_cpu = await _run_cmd("ps aux --sort=-%cpu 2>/dev/null | head -8")
            if not top_cpu:
                top_cpu = await _run_cmd("ps aux | head -8")

            sections.append(
                f"\n📊 TOP PROCESSES (by CPU)\n"
                f"{'─' * 50}\n"
                f"{top_cpu}"
            )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = (
            f"╔══════════════════════════════════════════════════╗\n"
            f"║        🔍 SYSTEM INFORMATION REPORT             ║\n"
            f"║        {timestamp}                    ║\n"
            f"╚══════════════════════════════════════════════════╝\n"
        )
        return header + "\n".join(sections)

    except Exception as e:
        log.error("system_info error", error=str(e))
        return f"❌ Error mengambil info sistem: {e}"


# ── 2. process_manager ───────────────────────────────────────────────────────

async def process_manager(action: str, target: str = None) -> str:
    """
    Kelola proses yang berjalan di server.

    Args:
        action: 'list', 'find', 'kill', 'ports', 'services'
        target: PID (untuk kill), nama proses (untuk find), port (untuk ports)

    Returns:
        Hasil operasi terstruktur
    """
    try:
        action = action.lower().strip()

        # ── List all processes ───────────────────────────────────────────
        if action == "list":
            result = await _run_cmd(
                "ps aux --sort=-%mem 2>/dev/null | head -30",
                timeout=15.0
            )
            return (
                f"📋 PROSES AKTIF (Top 30 by Memory)\n"
                f"{'═' * 60}\n"
                f"{result}\n"
                f"{'═' * 60}\n"
                f"Total: {await _run_cmd('ps aux | wc -l')} proses"
            )

        # ── Find process by name ─────────────────────────────────────────
        elif action == "find":
            if not target:
                return "❌ Parameter 'target' diperlukan untuk action 'find'. Contoh: process_manager('find', 'python')"

            result = await _run_cmd(
                f"ps aux | grep -i '{target}' | grep -v grep",
                timeout=10.0
            )
            if not result:
                return f"🔍 Tidak ditemukan proses yang cocok dengan '{target}'"

            count = len(result.strip().split("\n"))
            return (
                f"🔍 PROSES DITEMUKAN: '{target}' ({count} proses)\n"
                f"{'═' * 60}\n"
                f"{result}"
            )

        # ── Kill process by PID ──────────────────────────────────────────
        elif action == "kill":
            if not target:
                return "❌ Parameter 'target' (PID) diperlukan untuk action 'kill'."

            try:
                pid = int(target)
            except ValueError:
                # Target is a name, find PID first
                pids_raw = await _run_cmd(
                    f"pgrep -f '{target}' 2>/dev/null"
                )
                if not pids_raw:
                    return f"❌ Tidak ditemukan proses dengan nama '{target}'"
                pids = pids_raw.strip().split("\n")
                pid = int(pids[0])  # Kill first match

            if pid in _PROTECTED_PIDS:
                return f"🛡️ PID {pid} dilindungi (system critical). Tidak bisa di-kill."

            # Check if it's a protected process name
            proc_name = await _run_cmd(f"ps -p {pid} -o comm= 2>/dev/null")
            if any(pn in proc_name.lower() for pn in _PROTECTED_PROCESS_NAMES):
                return f"🛡️ Proses '{proc_name}' (PID {pid}) dilindungi (system critical). Tidak bisa di-kill."

            # Get process info before killing
            proc_info = await _run_cmd(f"ps -p {pid} -o pid,user,comm,args --no-headers 2>/dev/null")

            result = await _run_cmd(f"kill {pid} 2>&1")
            # Verify
            check = await _run_cmd(f"ps -p {pid} -o pid= 2>/dev/null")
            if check.strip():
                # Still alive, try SIGKILL
                await _run_cmd(f"kill -9 {pid} 2>&1")
                check2 = await _run_cmd(f"ps -p {pid} -o pid= 2>/dev/null")
                if check2.strip():
                    return f"⚠️ Proses {pid} tidak mau mati bahkan dengan SIGKILL"

            return (
                f"✅ PROSES BERHASIL DIHENTIKAN\n"
                f"{'═' * 60}\n"
                f"  PID          : {pid}\n"
                f"  Info         : {proc_info}\n"
                f"  Status       : Terminated"
            )

        # ── List listening ports ─────────────────────────────────────────
        elif action == "ports":
            if target:
                result = await _run_cmd(
                    f"ss -tlnp 2>/dev/null | grep ':{target} ' || lsof -i :{target} 2>/dev/null",
                    timeout=10.0
                )
                if not result:
                    return f"✅ Port {target} tidak digunakan (available)"
                return (
                    f"🔌 PORT {target}\n"
                    f"{'═' * 60}\n"
                    f"{result}"
                )
            else:
                result = await _run_cmd(
                    "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null",
                    timeout=10.0
                )
                return (
                    f"🔌 LISTENING PORTS\n"
                    f"{'═' * 60}\n"
                    f"{result}"
                )

        # ── List systemd services ────────────────────────────────────────
        elif action == "services":
            if target:
                result = await _run_cmd(
                    f"systemctl status {target} 2>/dev/null || service {target} status 2>/dev/null",
                    timeout=10.0
                )
                return (
                    f"🔧 SERVICE: {target}\n"
                    f"{'═' * 60}\n"
                    f"{result}"
                )
            else:
                result = await _run_cmd(
                    "systemctl list-units --type=service --state=running 2>/dev/null | head -25",
                    timeout=15.0
                )
                return (
                    f"🔧 RUNNING SERVICES\n"
                    f"{'═' * 60}\n"
                    f"{result}"
                )

        else:
            return (
                f"❌ Action '{action}' tidak dikenali.\n"
                f"Actions tersedia: list, find, kill, ports, services"
            )

    except Exception as e:
        log.error("process_manager error", error=str(e), action=action)
        return f"❌ Error process_manager: {e}"
