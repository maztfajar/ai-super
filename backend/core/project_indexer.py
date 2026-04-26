"""
AI ORCHESTRATOR — Project Indexer (Project-Wide Awareness)
Context Indexing: memetakan struktur file dan dependency antar file dalam proyek.
AI memahami keterkaitan antar file sehingga perubahan di satu file bisa
otomatis menyesuaikan file yang bergantung padanya.
"""
import os
import re
import json
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path
import structlog

log = structlog.get_logger()

# Max file/folder to scan to prevent overwhelming large repos
MAX_FILES = 500
MAX_FILE_SIZE_KB = 200  # Only parse files < 200KB for dependency detection
SCAN_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss',
    '.json', '.yaml', '.yml', '.md', '.txt', '.sh', '.bash',
    '.vue', '.svelte', '.go', '.rs', '.java', '.kt', '.rb', '.php',
}
IGNORE_DIRS = {
    'node_modules', '__pycache__', '.git', '.venv', 'venv', 'env',
    '.next', 'dist', 'build', '.cache', '.tox', 'vendor',
    'target', '.idea', '.vscode', 'coverage', '.mypy_cache',
}


class ProjectIndexer:
    async def scan_project(self, session_id: str, project_path: str) -> dict:
        """Scan folder proyek, bangun file tree + dependency graph. Simpan ke DB."""
        if not project_path or not os.path.isdir(project_path):
            return {"error": "Invalid project path", "files": 0}

        try:
            file_tree = []
            dependencies = {}  # {file_rel_path: [depends_on_rel_path, ...]}
            file_count = 0

            # Load gitignore patterns if available
            ignore_patterns = self._load_gitignore(project_path)

            for root, dirs, files in os.walk(project_path):
                # Prune ignored directories
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

                for fname in files:
                    if file_count >= MAX_FILES:
                        break

                    fpath = os.path.join(root, fname)
                    rel_path = os.path.relpath(fpath, project_path)

                    # Skip hidden files and non-tracked extensions
                    _, ext = os.path.splitext(fname)
                    if fname.startswith('.') and ext not in SCAN_EXTENSIONS:
                        continue
                    if ext not in SCAN_EXTENSIONS:
                        continue

                    # Check gitignore
                    if ignore_patterns and self._is_ignored(rel_path, ignore_patterns):
                        continue

                    try:
                        stat = os.stat(fpath)
                        size_kb = stat.st_size / 1024
                    except OSError:
                        continue

                    file_info = {
                        "path": rel_path,
                        "ext": ext,
                        "size_kb": round(size_kb, 1),
                    }
                    file_tree.append(file_info)
                    file_count += 1

                    # Parse dependencies jika file cukup kecil
                    if size_kb <= MAX_FILE_SIZE_KB:
                        try:
                            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            deps = self._detect_dependencies(rel_path, content, ext)
                            if deps:
                                dependencies[rel_path] = deps
                        except Exception:
                            pass

                if file_count >= MAX_FILES:
                    break

            # Simpan ke database
            await self._save_index(session_id, project_path, file_tree, dependencies, file_count)

            log.info("Project indexed", path=project_path,
                     files=file_count, deps=len(dependencies))

            return {
                "files": file_count,
                "dependencies": len(dependencies),
                "path": project_path,
            }

        except Exception as e:
            log.warning("Project scan failed", error=str(e)[:100])
            return {"error": str(e)[:100], "files": 0}

    def _detect_dependencies(self, file_path: str, content: str, ext: str) -> list:
        """Parse import/require/include statements dari file."""
        deps = []

        if ext in ('.py',):
            # Python: import x, from x import y
            for m in re.finditer(r'^(?:from\s+(\S+)\s+import|import\s+(\S+))', content, re.MULTILINE):
                module = m.group(1) or m.group(2)
                if module and not module.startswith(('os', 'sys', 'json', 're', 'asyncio',
                    'typing', 'datetime', 'pathlib', 'collections', 'functools',
                    'dataclasses', 'abc', 'enum', 'io', 'math', 'hashlib',
                    'base64', 'uuid', 'time', 'logging', 'copy', 'itertools')):
                    # Convert module path to file path
                    dep_path = module.replace('.', '/') + '.py'
                    deps.append(dep_path)

        elif ext in ('.js', '.jsx', '.ts', '.tsx', '.mjs'):
            # JS/TS: import ... from '...', require('...')
            for m in re.finditer(r'''(?:import\s+.*?\s+from\s+['"](.+?)['"]|require\s*\(\s*['"](.+?)['"]\s*\))''', content):
                dep = m.group(1) or m.group(2)
                if dep and dep.startswith(('./', '../')):
                    deps.append(dep)

        elif ext in ('.html',):
            # HTML: src="...", href="..."
            for m in re.finditer(r'(?:src|href)=["\']([^"\']+?\.(?:js|css|jsx|ts))["\']', content):
                dep = m.group(1)
                if not dep.startswith(('http', '//')):
                    deps.append(dep)

        elif ext in ('.css', '.scss'):
            # CSS: @import '...'
            for m in re.finditer(r'@import\s+["\'](.+?)["\']', content):
                deps.append(m.group(1))

        return deps[:20]  # Limit per file

    async def get_affected_files(self, session_id: str, changed_file: str) -> list:
        """Cari file yang bergantung pada changed_file (reverse dependency)."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import ProjectIndex
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                stmt = (select(ProjectIndex)
                        .where(ProjectIndex.session_id == session_id)
                        .order_by(ProjectIndex.last_scanned_at.desc())
                        .limit(1))
                result = await db.execute(stmt)
                index = result.scalars().first()
                if not index:
                    return []

                deps = json.loads(index.dependencies_json)
                affected = []
                changed_normalized = changed_file.replace('\\', '/')

                for file_path, file_deps in deps.items():
                    for dep in file_deps:
                        dep_normalized = dep.replace('\\', '/')
                        if (changed_normalized in dep_normalized or
                                dep_normalized.endswith(changed_normalized) or
                                os.path.splitext(changed_normalized)[0] in dep_normalized):
                            affected.append(file_path)
                            break

                return affected

        except Exception as e:
            log.debug("get_affected_files error", error=str(e)[:80])
            return []

    async def get_project_summary(self, session_id: str) -> str:
        """Buat ringkasan proyek untuk injeksi ke prompt AI."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import ProjectIndex
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                stmt = (select(ProjectIndex)
                        .where(ProjectIndex.session_id == session_id)
                        .order_by(ProjectIndex.last_scanned_at.desc())
                        .limit(1))
                result = await db.execute(stmt)
                index = result.scalars().first()
                if not index:
                    return ""

                file_tree = json.loads(index.file_tree_json)
                deps = json.loads(index.dependencies_json)

                if not file_tree:
                    return ""

                # Buat ringkasan singkat
                ext_counts = {}
                for f in file_tree:
                    ext = f.get("ext", "")
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1

                parts = [
                    f"\n[PROJECT CONTEXT — {index.project_path}]",
                    f"Total files: {index.file_count}",
                    "File types: " + ", ".join(f"{ext}({c})" for ext, c in sorted(ext_counts.items(), key=lambda x: -x[1])[:8]),
                ]

                # Top-level structure
                top_files = [f["path"] for f in file_tree if '/' not in f["path"]][:15]
                if top_files:
                    parts.append("Root files: " + ", ".join(top_files))

                # Key dependency info
                if deps:
                    dep_count = sum(len(v) for v in deps.values())
                    parts.append(f"Dependencies tracked: {len(deps)} files, {dep_count} links")

                    # Most-depended-on files (hub files)
                    dep_targets = {}
                    for file_path, file_deps in deps.items():
                        for dep in file_deps:
                            dep_targets[dep] = dep_targets.get(dep, 0) + 1
                    if dep_targets:
                        hubs = sorted(dep_targets.items(), key=lambda x: -x[1])[:5]
                        parts.append("Key files (most imported): " +
                                     ", ".join(f"{h[0]}({h[1]}x)" for h in hubs))

                parts.append("[/PROJECT CONTEXT]")
                return "\n".join(parts)

        except Exception as e:
            log.debug("get_project_summary error", error=str(e)[:80])
            return ""

    async def _save_index(self, session_id: str, project_path: str,
                          file_tree: list, dependencies: dict, file_count: int):
        """Simpan/update index ke database."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import ProjectIndex
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                stmt = (select(ProjectIndex)
                        .where(ProjectIndex.session_id == session_id)
                        .limit(1))
                result = await db.execute(stmt)
                existing = result.scalars().first()

                now = datetime.now(timezone.utc).replace(tzinfo=None)

                if existing:
                    existing.project_path = project_path
                    existing.file_tree_json = json.dumps(file_tree, ensure_ascii=False)
                    existing.dependencies_json = json.dumps(dependencies, ensure_ascii=False)
                    existing.file_count = file_count
                    existing.last_scanned_at = now
                    db.add(existing)
                else:
                    idx = ProjectIndex(
                        session_id=session_id, project_path=project_path,
                        file_tree_json=json.dumps(file_tree, ensure_ascii=False),
                        dependencies_json=json.dumps(dependencies, ensure_ascii=False),
                        file_count=file_count, last_scanned_at=now, created_at=now,
                    )
                    db.add(idx)
                await db.commit()

        except Exception as e:
            log.warning("Failed to save project index", error=str(e)[:100])

    def _load_gitignore(self, project_path: str) -> list:
        """Load .gitignore patterns."""
        gitignore = os.path.join(project_path, '.gitignore')
        if not os.path.exists(gitignore):
            return []
        try:
            with open(gitignore, 'r') as f:
                patterns = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
                return patterns
        except Exception:
            return []

    def _is_ignored(self, rel_path: str, patterns: list) -> bool:
        """Simple gitignore-style check."""
        for pattern in patterns:
            pattern = pattern.rstrip('/')
            if pattern in rel_path or rel_path.startswith(pattern):
                return True
        return False


project_indexer = ProjectIndexer()
