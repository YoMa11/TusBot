# --- file version marker ---
__file_version__ = "release.sh@1"  # created 2025-08-29 22:59
#!/usr/bin/env bash
set -euo pipefail

# ==== הגדרות ====
PROJECT_NAME="${PROJECT_NAME:-tusbot}"   # אפשר לשנות עם --name
BASE_DIR="$(pwd)"
OLD_DIR="${BASE_DIR}/old"

# תבניות להחרגה (לא ייכנסו לחבילה)
EXCLUDES=(
  ".venv"
  "old"
  "*.zip"
  "__pycache__"
  ".pytest_cache"
  ".mypy_cache"
  ".ruff_cache"
  ".git"
  ".git/*"
  ".DS_Store"
  "*.pyc"
  "bot.log"
  "bot.err.log"
  "_debug_*"
)

INCLUDE_DB="${INCLUDE_DB:-1}"     # 1 כדי לכלול *.db באריזה
CHMOD_TARGET="${CHMOD:777}"         # 777 כדי לכפות הרשאות
OUT_DIR="${OUT_DIR:-/Users/yossimantsour/Desktop/tusbot}"            # אם מוגדר - הזזת ה-ZIP לנתיב הזה


# ==== פרמטרים ====
BUMP="patch"
KEEP_STAGE=0
SET_VERSION=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --major|--minor|--patch) BUMP="${1#--}";;
    --set) SET_VERSION="${2:-}"; shift;;
    --keep) KEEP_STAGE=1;;
    --name) PROJECT_NAME="${2:-$PROJECT_NAME}"; shift;;
    --include-db) INCLUDE_DB=1;;
    --help)
      cat <<USAGE
usage: ./releases.sh [--major|--minor|--patch] [--set X.Y.Z] [--keep] [--name NAME] [--include-db]
env:   PROJECT_NAME, INCLUDE_DB=1, CHMOD=777
USAGE
      exit 0;;
    *) echo "⚠️ Unknown arg: $1" ;;
  esac
  shift
done

# ==== בדיקות כלי עזר ====
command -v zip >/dev/null 2>&1 || { echo "❌ zip לא מותקן"; exit 1; }
command -v rsync >/dev/null 2>&1 || { echo "❌ rsync לא מותקן"; exit 1; }

# ==== מציאת גרסה נוכחית ====
if [[ -n "$SET_VERSION" ]]; then
  version="$SET_VERSION"
elif [[ -f VERSION ]]; then
  version="$(tr -d '\n' < VERSION)"
elif latest_zip="$(ls -1 "${PROJECT_NAME}"_v*.zip 2>/dev/null | \
         sed -E 's/.*_v([0-9]+)\.([0-9]+)\.([0-9]+)\.zip/\1 \2 \3 &/' | \
         sort -n -k1,1 -k2,2 -k3,3 | awk '{print $4}' | tail -n1 || true)"; [[ -n "$latest_zip" ]]; then
  base="$(basename "$latest_zip")"
  version="${base#${PROJECT_NAME}_v}"
  version="${version%.zip}"
else
  version="1.0.0"
fi

IFS='.' read -r MA MI PA <<<"$version"
case "$BUMP" in
  major) MA=$((MA+1)); MI=0; PA=0;;
  minor) MI=$((MI+1)); PA=0;;
  patch) PA=$((PA+1));;
  *) echo "⚠️ Unknown BUMP=$BUMP, using patch"; PA=$((PA+1));;
esac
new_version="${MA}.${MI}.${PA}"

stage="${PROJECT_NAME}_v${new_version}"
zip_name="${stage}.zip"

echo "📦 Packaging ${PROJECT_NAME} → v${new_version}"

# כתיבת VERSION לעתיד
printf '%s\n' "$new_version" > VERSION

# ==== העברת ZIPים/תיקיות ישנות ל-old/ ====
mkdir -p "$OLD_DIR"

# Move previous zips (שומרים עץ נקי)
shopt -s nullglob
for z in "${PROJECT_NAME}"_v*.zip; do
  [[ "$z" == "$zip_name" ]] && continue
  mv -f "$z" "$OLD_DIR/"
done
# Move previous stage dirs (אם נשארו)
for d in "${PROJECT_NAME}"_v*; do
  [[ -d "$d" ]] || continue
  [[ "$d" == "$stage" ]] && continue
  [[ "$d" == "old" ]] && continue
  mv -f "$d" "$OLD_DIR/" || true
done
shopt -u nullglob

# ==== הכנת stage ====
rm -rf "$stage"
mkdir -p "$stage"

# ניקוי אוטומטי של stage אם לא ביקשת לשמור
cleanup() {
  if [[ $KEEP_STAGE -eq 0 ]]; then
    rm -rf "$stage"
  fi
}
trap cleanup EXIT

# exclude list ל-rsync (כולל החרגת תיקיית ה-stage החדשה למניעת self-copy)
rsync_ex=()
for e in "${EXCLUDES[@]}"; do rsync_ex+=(--exclude "$e"); done
rsync_ex+=(--exclude "$stage")
# exclude DBs אם לא ביקשת לכלול
if [[ "$INCLUDE_DB" -eq 0 ]]; then
  rsync_ex+=(--exclude "flights.db" --exclude "flights.db-*"
             --exclude "*.db" --exclude "*.db-wal" --exclude "*.db-shm")
fi

# העתקה נקייה אל stage
rsync -a --delete "${rsync_ex[@]}" ./ "$stage/"

# הרשאות
if [[ -n "$CHMOD_TARGET" ]]; then
  chmod -R "$CHMOD_TARGET" "$stage"
else
  find "$stage" -type d -exec chmod 755 {} \; 2>/dev/null || true
  find "$stage" -type f -exec chmod 644 {} \; 2>/dev/null || true
  for f in app.py debug_scrape_once.py botctl.sh; do
    [[ -f "$stage/$f" ]] && chmod 755 "$stage/$f"
  done
fi

# עדכון גרסה פנימית (אופציונלי): SCRIPT_VERSION אם קיים ב-config.py, בלי ליגע ב-BOT_TOKEN/URL
if [[ -f "$stage/config.py" ]]; then
  # שמור את הפורמט "Vx.y.z" כפי שהיה אצלך
  perl -0777 -pe 's/(SCRIPT_VERSION\s*=\s*")[^"]+(")/${1}V'"$new_version"'${2}/g' \
    -i "$stage/config.py" || true
fi

# ==== יצירת ZIP ====
# מוודאים שלא קיים ZIP עם אותו שם כבר בשורש (למנוע overwrite שקט)
[[ -f "$zip_name" ]] && mv -f "$zip_name" "$OLD_DIR/" || true

zip -qr9 "$zip_name" "$stage"

# checksum
if command -v shasum >/dev/null 2>&1; then
  sha=$(shasum -a 256 "$zip_name" | awk '{print $1}')
  echo "✅ Created: $zip_name"
  echo "🔐 sha256: $sha"
else
  echo "✅ Created: $zip_name (install coreutils for sha256sum)"
fi


# ==== הזזת ה-ZIP ליעד אם OUT_DIR מוגדר ====
if [[ -n "$OUT_DIR" ]]; then
  mkdir -p "$OUT_DIR"
  mv -f "${stage}.zip" "$OUT_DIR/"
  [[ -f "${stage}.zip.sha256" ]] && mv -f "${stage}.zip.sha256" "$OUT_DIR/" || true
  echo "📦 Output placed at: $OUT_DIR/${stage}.zip"
fi


# אם ביקשת לשמור את stage, לא ננקה ב-exit
if [[ $KEEP_STAGE -eq 1 ]]; then
  trap - EXIT
  echo "📁 Stage kept at: $stage/"
fi

echo "📂 Previous archives & stages moved to: $OLD_DIR"
