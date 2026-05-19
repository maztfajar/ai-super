"""
ProjectContextLoader — Baca file tree + dependencies project sebelum edit apapun.
Simpan snapshot ke DB (ProjectIndex). Load ke context setiap kali project dibuka.
"""
import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import structlog

log = structlog.get_logger()

# File yang relevan untuk di-index (skip binary, node_modules, dll)
_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "coverage", ".cache",
}
_RELEVANT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
    ".json", ".yaml", ".yml", ".env.example", ".md",
    ".go", ".rs", ".java", ".php", ".rb", ".sh",
}
_MAX_FILES = 200  # batas agar tidak overload context


def _scan_file_tree(root_path: str) -> List[Dict[str, Any]]:
    """Scan directory dan kembalikan list file dengan metadata."""
    files = []
    try:
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Skip direktori yang tidak relevan
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]

            for fname in filenames:
                _, ext = os.path.splitext(fname)
                if ext.lower() not in _RELEVANT_EXTENSIONS:
                    continue

                full_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(full_path, root_path)
                try:
                    size = os.path.getsize(full_path)
                    files.append({
                        "path": rel_path,
                        "size_bytes": size,
                        "extension": ext.lower(),
                    })
                except OSError:
                    continue

                if len(files) >= _MAX_FILES:
                    return files
    except Exception as e:
        log.warning("File tree scan error", error=str(e)[:100])
    return files


def _parse_dependencies(root_path: str) -> Dict[str, Any]:
    """Extract dependencies dari package.json atau requirements.txt."""
    deps = {}

    # Node.js
    pkg_path = os.path.join(root_path, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                pkg = json.load(f)
            deps["runtime"] = list(pkg.get("dependencies", {}).keys())
            deps["dev"] = list(pkg.get("devDependencies", {}).keys())
            deps["framework"] = _detect_framework_from_pkg(pkg)
        except Exception:
            pass

    # Python
    req_path = os.path.join(root_path, "requirements.txt")
    if os.path.exists(req_path):
        try:
            with open(req_path, "r", encoding="utf-8") as f:
                lines = [l.strip().split("==")[0].split(">=")[0]
                         for l in f if l.strip() and not l.startswith("#")]
            deps["python"] = lines[:50]
        except Exception:
            pass

    return deps


def _detect_framework_from_pkg(pkg: dict) -> str:
    all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    if "next" in all_deps:
        return "Next.js"
    if "react" in all_deps:
        return "React"
    if "vue" in all_deps:
        return "Vue"
    if "svelte" in all_deps:
        return "Svelte"
    if "express" in all_deps:
        return "Express"
    return "Node.js"


def _list_components(files: List[Dict]) -> List[str]:
    """Extract nama komponen dari file tree."""
    components = []
    for f in files:
        path = f["path"]
        ext = f["extension"]
        if ext in {".jsx", ".tsx", ".vue"}:
            name = os.path.basename(path).replace(ext, "")
            if name[0].isupper():  # PascalCase = komponen
                components.append(name)
        elif ext == ".py" and ("model" in path.lower() or "view" in path.lower()):
            components.append(os.path.basename(path).replace(".py", ""))
    return components[:30]


async def load_project_context(
    session_id: str,
    project_path: str,
    force_rescan: bool = False,
) -> str:
    """
    Load project context untuk session ini.
    Scan file tree, parse dependencies, simpan ke DB, return context string.

    Args:
        session_id: ID session saat ini
        project_path: path absolut ke root project
        force_rescan: paksa rescan meski sudah ada di DB

    Returns:
        String context yang siap di-inject ke system prompt.
    """
    if not project_path or not os.path.isdir(project_path):
        return ""

    # Cek apakah sudah ada di DB dan masih fresh (< 10 menit)
    if not force_rescan:
        cached = await _load_from_db(session_id)
        if cached:
            return _format_context(cached["files"], cached["deps"], project_path)

    # Scan project
    files = _scan_file_tree(project_path)
    deps = _parse_dependencies(project_path)

    # Simpan ke DB
    await _save_to_db(session_id, project_path, files, deps)

    return _format_context(files, deps, project_path)


def _format_context(
    files: List[Dict],
    deps: Dict[str, Any],
    project_path: str,
) -> str:
    """Format context string untuk di-inject ke system prompt."""
    if not files:
        return ""

    components = _list_components(files)
    file_list = "\n".join(f"  - {f['path']}" for f in files[:50])
    if len(files) > 50:
        file_list += f"\n  ... dan {len(files) - 50} file lainnya"

    stack_parts = []
    if deps.get("framework"):
        stack_parts.append(deps["framework"])
    if deps.get("python"):
        stack_parts.append("Python")
    stack_str = ", ".join(stack_parts) if stack_parts else "Unknown"

    lines = [
        "\n[PROJECT CONTEXT — BACA SEBELUM EDIT APAPUN]",
        f"Root: {project_path}",
        f"Stack: {stack_str}",
        f"Total files: {len(files)}",
        "",
        "File yang sudah ada:",
        file_list,
    ]
    if components:
        lines.append(f"\nKomponen yang sudah ada: {', '.join(components)}")
    lines.append("\nATURAN: JANGAN buat file yang sudah ada di atas. SELALU baca file dulu sebelum edit.")

    return "\n".join(lines)


async def _load_from_db(session_id: str) -> Optional[Dict]:
    """Load ProjectIndex dari DB jika masih fresh."""
    try:
        from db.database import AsyncSessionLocal
        from db.models import ProjectIndex
        from sqlmodel import select

        async with AsyncSessionLocal() as db:
            stmt = select(ProjectIndex).where(ProjectIndex.session_id == session_id)
            result = await db.execute(stmt)
            pi = result.scalar_one_or_none()
            if not pi:
                return None

            # Cek freshness (10 menit)
            age = (datetime.utcnow() - pi.last_scanned_at).total_seconds()
            if age > 600:
                return None

            return {
                "files": json.loads(pi.file_tree_json),
                "deps": json.loads(pi.dependencies_json),
            }
    except Exception as e:
        log.debug("ProjectIndex load failed", error=str(e)[:80])
        return None


async def _save_to_db(
    session_id: str,
    project_path: str,
    files: List[Dict],
    deps: Dict,
) -> None:
    """Upsert ProjectIndex ke DB."""
    try:
        from db.database import AsyncSessionLocal
        from db.models import ProjectIndex
        from sqlmodel import select

        async with AsyncSessionLocal() as db:
            stmt = select(ProjectIndex).where(ProjectIndex.session_id == session_id)
            result = await db.execute(stmt)
            pi = result.scalar_one_or_none()

            now = datetime.utcnow()
            if pi:
                pi.project_path = project_path
                pi.file_tree_json = json.dumps(files, ensure_ascii=False)
                pi.dependencies_json = json.dumps(deps, ensure_ascii=False)
                pi.file_count = len(files)
                pi.last_scanned_at = now
                db.add(pi)
            else:
                db.add(ProjectIndex(
                    session_id=session_id,
                    project_path=project_path,
                    file_tree_json=json.dumps(files, ensure_ascii=False),
                    dependencies_json=json.dumps(deps, ensure_ascii=False),
                    file_count=len(files),
                    last_scanned_at=now,
                ))
            await db.commit()
    except Exception as e:
        log.warning("Failed to save ProjectIndex", error=str(e)[:100])
