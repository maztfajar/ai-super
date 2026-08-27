#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# safe_exec.sh — Bubblewrap Sandbox Wrapper for AI Orchestrator
# ═══════════════════════════════════════════════════════════════════════
# Usage: ./safe_exec.sh <workspace_dir> <profile> <network> <command...>
#
# Profiles:
#   read_only   — Read-only filesystem, no network
#   write_safe  — Read + write in workspace, no network
#   full_access — Full read/write, network enabled
#
# Examples:
#   ./safe_exec.sh /home/user/projects write_safe offline "npm run build"
#   ./safe_exec.sh /home/user/projects read_only offline "cat package.json"
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

WORKSPACE_DIR="${1:?Usage: safe_exec.sh <workspace_dir> <profile> <network> <command>}"
PROFILE="${2:-write_safe}"
NETWORK="${3:-offline}"
shift 3
COMMAND="$*"

if [ -z "$COMMAND" ]; then
    echo "Error: No command specified" >&2
    exit 1
fi

# Check bwrap availability
if ! command -v bwrap &>/dev/null; then
    echo "Warning: bwrap not found, executing without sandbox" >&2
    cd "$WORKSPACE_DIR" && eval "$COMMAND"
    exit $?
fi

# ── Build bwrap flags ─────────────────────────────────────────────────

BWRAP_FLAGS=()

# System paths (read-only)
for sys_path in /usr /lib /lib64 /bin /sbin; do
    if [ -d "$sys_path" ]; then
        BWRAP_FLAGS+=(--ro-bind "$sys_path" "$sys_path")
    fi
done

# SSL certs & DNS (read-only)
for ro_path in /etc/ssl /etc/resolv.conf /etc/hosts /etc/alternatives /etc/ld.so.cache; do
    if [ -e "$ro_path" ]; then
        BWRAP_FLAGS+=(--ro-bind "$ro_path" "$ro_path")
    fi
done

# Home directory tools (read-only)
HOME_DIR="${HOME:-/root}"
for home_sub in .local .npm .cache .config .cargo .rustup; do
    if [ -d "$HOME_DIR/$home_sub" ]; then
        BWRAP_FLAGS+=(--ro-bind "$HOME_DIR/$home_sub" "$HOME_DIR/$home_sub")
    fi
done

# Profile-specific binds
case "$PROFILE" in
    read_only)
        BWRAP_FLAGS+=(--ro-bind "$WORKSPACE_DIR" "$WORKSPACE_DIR")
        ;;
    write_safe)
        BWRAP_FLAGS+=(--bind "$WORKSPACE_DIR" "$WORKSPACE_DIR")
        ;;
    full_access)
        BWRAP_FLAGS+=(--bind "$WORKSPACE_DIR" "$WORKSPACE_DIR")
        # Also bind /opt if exists
        if [ -d /opt ]; then
            BWRAP_FLAGS+=(--bind /opt /opt)
        fi
        ;;
    *)
        echo "Error: Unknown profile '$PROFILE'" >&2
        exit 1
        ;;
esac

# Virtual filesystems
BWRAP_FLAGS+=(--proc /proc --dev /dev --tmpfs /tmp)

# Working directory
BWRAP_FLAGS+=(--chdir "$WORKSPACE_DIR")

# Network isolation
if [ "$NETWORK" = "offline" ]; then
    BWRAP_FLAGS+=(--unshare-net)
fi

# Process isolation
BWRAP_FLAGS+=(--unshare-pid --die-with-parent)

# ── Execute ───────────────────────────────────────────────────────────

exec bwrap "${BWRAP_FLAGS[@]}" -- bash -c "$COMMAND"
