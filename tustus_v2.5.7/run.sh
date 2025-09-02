#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PY_MIN="3.10.0"
VENV_DIR="${PROJECT_DIR}/.venv"
REQ="${PROJECT_DIR}/requirements.txt"

version_ge() {
  # compare two versions: $1 >= $2 ?
  python3 - <<PY
import sys
from packaging.version import Version as V
print("1" if V(sys.argv[1]) >= V(sys.argv[2]) else "0")
PY "$1" "$2"
}

ensure_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 not found. Please install Python ${PY_MIN}+."
    exit 1
  fi
  local VER
  VER="$(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:3])))')"
  if [[ "$(version_ge "$VER" "$PY_MIN")" != "1" ]]; then
    echo "❌ Python version $VER is too old. Need ${PY_MIN}+."
    exit 1
  fi
}

ensure_venv() {
  if [[ ! -x "${VENV_DIR}/bin/python3" ]]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
  fi
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  python -m pip install --upgrade pip wheel setuptools
  if [[ -f "$REQ" ]]; then
    echo "📦 Installing requirements..."
    pip install -r "$REQ"
  else
    echo "⚠️ requirements.txt not found. Skipping."
  fi
}

usage() {
  echo "Usage: $0 [dev|daemon]"
  echo "  dev    - run in foreground (default)"
  echo "  daemon - run as background service via botctl.sh"
}

cmd="${1:-dev}"

ensure_python
ensure_venv

case "$cmd" in
  dev)
    echo "▶️  Running app.py in foreground..."
    exec python app.py
    ;;
  daemon)
    echo "▶️  Starting daemon via botctl.sh..."
    exec ./botctl.sh start
    ;;
  *)
    usage
    exit 2
    ;;
esac
