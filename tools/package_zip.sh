#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "$ROOT/VERSION" | tr -d '\n')"
NAME="tusbot_v${VERSION}"
DIST="$ROOT/dist"
OLD="$DIST/old"

mkdir -p "$OLD"

# להזיז ZIPים קודמים ל-old
find "$DIST" -maxdepth 1 -type f -name "tusbot_v*.zip" -exec mv {} "$OLD"/ \; || true

TMP="$ROOT/.package_tmp"
rm -rf "$TMP"
mkdir -p "$TMP/$NAME"

# העתקת קבצים נקיים
rsync -a --exclude '.git' \
       --exclude '.github' \
       --exclude '.venv' \
       --exclude 'dist' \
       --exclude 'old' \
       --exclude '__pycache__' \
       --exclude '*.pyc' \
       "$ROOT/" "$TMP/$NAME/"

# יצירת ה-ZIP (כולל תיקיה פנימית בשם הגרסה)
mkdir -p "$DIST"
( cd "$TMP" && zip -r "$DIST/$NAME.zip" "$NAME" >/dev/null )

rm -rf "$TMP"

echo "✅ Built $DIST/$NAME.zip"
