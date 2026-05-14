import os
import re
import argparse

def bump_version(part="patch"):
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_file):
        print(f"Error: {env_file} tidak ditemukan.")
        return

    with open(env_file, "r") as f:
        content = f.read()

    # Cari baris APP_VERSION
    match = re.search(r'APP_VERSION\s*=\s*["\']?(\d+)\.(\d+)\.(\d+)["\']?', content)
    if not match:
        print("Error: Format APP_VERSION tidak ditemukan di .env.")
        return

    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    old_version = f"{major}.{minor}.{patch}"

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    new_version = f"{major}.{minor}.{patch}"
    new_content = re.sub(
        r'(APP_VERSION\s*=\s*["\']?)\d+\.\d+\.\d+(["\']?)',
        rf'\g<1>{new_version}\g<2>',
        content
    )

    with open(env_file, "w") as f:
        f.write(new_content)

    print(f"Versi berhasil diupdate: {old_version} -> {new_version}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bump APP_VERSION di .env")
    parser.add_argument("part", choices=["major", "minor", "patch"], nargs="?", default="patch", help="Bagian versi yang ingin dinaikkan (default: patch)")
    args = parser.parse_args()
    bump_version(args.part)
