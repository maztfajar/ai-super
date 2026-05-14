import os
import re
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
VERSION_FILE = ROOT / "VERSION"


def bump_version(part="patch"):
    # ── Baca versi saat ini dari VERSION file (sumber kebenaran) ──────────
    if VERSION_FILE.exists():
        current = VERSION_FILE.read_text(encoding="utf-8").strip()
    elif ENV_FILE.exists():
        m = re.search(r'APP_VERSION\s*=\s*["\']?(\d+\.\d+\.\d+)["\']?', ENV_FILE.read_text())
        current = m.group(1) if m else "1.0.0"
    else:
        current = "1.0.0"

    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', current)
    if not match:
        print(f"Error: Format versi tidak valid: '{current}'")
        return

    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    old_version = f"{major}.{minor}.{patch}"

    if part == "major":
        major += 1; minor = 0; patch = 0
    elif part == "minor":
        minor += 1; patch = 0
    else:
        patch += 1

    new_version = f"{major}.{minor}.{patch}"

    # ── Update VERSION file (dibaca oleh Docker image) ────────────────────
    VERSION_FILE.write_text(new_version + "\n", encoding="utf-8")

    # ── Sync ke .env agar konsisten di lingkungan lokal ───────────────────
    if ENV_FILE.exists():
        content = ENV_FILE.read_text(encoding="utf-8")
        new_content = re.sub(
            r'(APP_VERSION\s*=\s*["\']?)\d+\.\d+\.\d+(["\']?)',
            rf'\g<1>{new_version}\g<2>',
            content
        )
        ENV_FILE.write_text(new_content, encoding="utf-8")

    print(f"✅ Versi diupdate: {old_version} → {new_version}")
    print(f"   VERSION file : {VERSION_FILE}")
    if ENV_FILE.exists():
        print(f"   .env synced  : {ENV_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bump APP_VERSION di VERSION file dan .env")
    parser.add_argument("part", choices=["major", "minor", "patch"], nargs="?", default="patch")
    args = parser.parse_args()
    bump_version(args.part)
