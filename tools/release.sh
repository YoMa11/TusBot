#!/usr/bin/env bash
set -euo pipefail

KIND="${1:-patch}"            # major|minor|patch|prerelease
MSG="${2:-chore(release)}"    # הודעת קומיט אופציונלית

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ודא שאין שינויים לא שמורים
if [[ -n "$(git status --porcelain)" ]]; then
  echo "❌ Working tree not clean. Commit/stash first."
  git status
  exit 1
fi

# (אם יש בדיקות/לינטרים - אפשר להריץ כאן)

# העלאת גרסה + עידכון changelog
NEW_VER="$(python3 "$ROOT/tools/bump_version.py" "$KIND")"
TAG="v$NEW_VER"

# קומיט של VERSION+CHANGELOG ותגית
git add VERSION CHANGELOG.md
git commit -m "chore(release): $NEW_VER"
git tag -a "$TAG" -m "Release $TAG"

# בניית ה-ZIP
"$ROOT/tools/package_zip.sh"

# דחיפה ל-remote
git push origin HEAD
git push origin "$TAG"

echo "✅ Released $TAG"
echo "ZIP at: $ROOT/dist/tusbot_v$NEW_VER.zip"
