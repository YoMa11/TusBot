#!/usr/bin/env python3
import sys, re, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"

def read_version():
    return VERSION_FILE.read_text().strip()

def write_version(v):
    VERSION_FILE.write_text(v + "\n")

def bump(v, kind):
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$", v)
    if not m:
        raise SystemExit(f"Invalid version: {v}")
    major, minor, patch, pre = m.groups()
    major, minor, patch = map(int, (major, minor, patch))

    if kind == "major":
        major, minor, patch, pre = major+1, 0, 0, None
    elif kind == "minor":
        minor, patch, pre = minor+1, 0, None
    elif kind == "patch":
        patch, pre = patch+1, None
    elif kind == "prerelease":
        if pre is None:
            pre = "rc.1"
        else:
            m2 = re.match(r"^(.*?)(\d+)$", pre)
            pre = f"{m2.group(1)}{int(m2.group(2))+1}" if m2 else pre + ".1"
    else:
        raise SystemExit("kind must be one of: major|minor|patch|prerelease")

    return f"{major}.{minor}.{patch}" + (f"-{pre}" if pre else "")

def update_changelog(new_v):
    # מוסיף כותרת לגרסה החדשה עם רשימת קומיטים מאז התגית האחרונה
    try:
        last_tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"], text=True
        ).strip()
        log = subprocess.check_output(
            ["git", "log", f"{last_tag}..HEAD", "--pretty=format:- %s"], text=True
        )
    except subprocess.CalledProcessError:
        log = subprocess.check_output(
            ["git", "log", "--pretty=format:- %s"], text=True
        )

    cl = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    header = f"\n\n## [{new_v}] - Auto\n{log or '- No changes recorded'}\n"
    (ROOT / "CHANGELOG.md").write_text(cl + header, encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: bump_version.py [major|minor|patch|prerelease]")
    kind = sys.argv[1]
    cur = read_version()
    new = bump(cur, kind)
    write_version(new)
    update_changelog(new)
    print(new)
