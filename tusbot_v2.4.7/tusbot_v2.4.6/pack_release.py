# --- file version marker ---
__file_version__ = "pack_release.py@1"  # created 2025-08-29 22:59

import os, zipfile, re, shutil, time, argparse, sys

def find_next_version(dst_dir):
    pat = re.compile(r"tustus_bot_inline_PRO_v(\d+)\.(\d+)\.(\d+)\.zip$")
    zips = [f for f in os.listdir(dst_dir) if pat.match(f)]
    if not zips:
        return (1,0,0)
    def ver_tuple(name):
        m = pat.match(name)
        return tuple(map(int, m.groups()))
    major, minor, patch = ver_tuple(max(zips, key=ver_tuple))
    return (major, minor, patch+1)

def main():
    ap = argparse.ArgumentParser(description="Package project into versioned zip and move old zips to ./old")
    ap.add_argument("--dir", default=".", help="Project root directory (default: current)")
    ap.add_argument("--version", default=None, help="Optional explicit version like 1.2.0")
    args = ap.parse_args()

    base = os.path.abspath(args.dir)
    old_dir = os.path.join(base, "old")
    os.makedirs(old_dir, exist_ok=True)

    if args.version:
        try:
            major, minor, patch = map(int, args.version.split("."))
            version = f"{major}.{minor}.{patch}"
        except Exception:
            print("Invalid --version. Use format X.Y.Z", file=sys.stderr)
            sys.exit(2)
    else:
        version = ".".join(map(str, find_next_version(base)))

    # move existing zips
    pat = re.compile(r"tustus_bot_inline_PRO_v(\d+)\.(\d+)\.(\d+)\.zip$")
    for f in os.listdir(base):
        if pat.match(f):
            shutil.move(os.path.join(base, f), os.path.join(old_dir, f))

    zip_name = f"tustus_bot_inline_PRO_v{version}.zip"
    zip_path = os.path.join(base, zip_name)

    # collect files recursively, excluding old/ and any .zip
    files = []
    for root, dirs, fnames in os.walk(base):
        if os.path.abspath(root).startswith(os.path.abspath(old_dir)):
            continue
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        for fn in fnames:
            if fn.lower().endswith(".zip"):
                continue
            full = os.path.join(root, fn)
            if os.path.abspath(full) == os.path.abspath(zip_path):
                continue
            files.append(full)

    # write VERSION, release notes, manifest
    version_file = os.path.join(base, "VERSION")
    with open(version_file, "w") as vf:
        vf.write(version)

    rn_path = os.path.join(base, "release_notes.txt")
    with open(rn_path, "a", encoding="utf-8") as rn:
        rn.write(f"Version {version} - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        rn.write("Packaged all project files recursively. Older zips moved to /old.\n\n")

    manifest = os.path.join(base, f"manifest_v{version}.txt")
    with open(manifest, "w", encoding="utf-8") as mf:
        mf.write(f"Manifest for {zip_name}\n")
        mf.write(f"Created at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        mf.write(f"Total files: {len(files)}\n\n")
        for p in sorted(files):
            mf.write(os.path.relpath(p, base) + "\n")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, arcname=os.path.relpath(f, base))
        z.write(version_file, arcname="VERSION")
        z.write(rn_path, arcname="release_notes.txt")
        z.write(manifest, arcname=os.path.basename(manifest))

    print(zip_path)

if __name__ == "__main__":
    main()
