#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

# Always run from the version folder only
export PYTHONPATH="$PWD"

VENV="$HERE/.venv"
PIDFILE="$HERE/bot.pid"
LOGFILE="$HERE/bot.log"
REQ="$HERE/requirements.txt"
REQHASH_FILE="$VENV/.req.hash"
PY_BIN="${PY_BIN:-python3}"

# Open permissions for all files (per user request)
chmod -R 777 "$HERE" || true

ensure_python() {
  if command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PY_BIN="python"
  fi
}

ensure_venv() {
  ensure_python
  if [[ ! -d "$VENV" ]]; then
    echo "[setup] creating venv at $VENV"
    "$PY_BIN" -m venv "$VENV"
  fi
}

venv_python() {
  if [[ -x "$VENV/bin/python" ]]; then
    echo "$VENV/bin/python"
  else
    echo "$PY_BIN"
  fi
}

calc_req_hash() {
  if [[ -f "$REQ" ]]; then
    if command -v shasum >/dev/null 2>&1; then
      shasum "$REQ" | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
      sha256sum "$REQ" | awk '{print $1}'
    else
      # fallback: contents md5 via python
      python3 - <<'PY'
import hashlib,sys
data=open(sys.argv[1],'rb').read()
print(hashlib.md5(data).hexdigest())
PY
      "$REQ"
    fi
  else
    echo "no-req-file"
  fi
}

install_requirements_if_needed() {
  ensure_venv
  PY="$(venv_python)"
  local need=0
  local newhash oldhash
  newhash="$(calc_req_hash)"
  oldhash="$(cat "$REQHASH_FILE" 2>/dev/null || true)"
  if [[ "$newhash" != "$oldhash" ]]; then
    need=1
  fi
  if [[ ! -x "$VENV/bin/pip" ]]; then
    need=1
  fi
  if [[ "$need" -eq 1 ]]; then
    echo "[setup] installing requirements ..."
    "$VENV/bin/pip" install --upgrade pip wheel setuptools
    if [[ -f "$REQ" ]]; then
      "$VENV/bin/pip" install -r "$REQ"
    fi
    echo "$newhash" > "$REQHASH_FILE"
    echo "[setup] requirements installed."
  fi
}

doctor() {
  ensure_venv
  "$VENV/bin/python" - <<'PY'
import sys
print("[doctor] Python:", sys.version)
try:
    import telegram, telegram.ext
    print("[doctor] python-telegram-bot:", getattr(telegram, "__version__", "OK"))
except Exception as e:
    print("[doctor] ERROR: telegram module not available:", e)
    sys.exit(1)
print("[doctor] OK")
PY
}

start() {
  install_requirements_if_needed
  PY="$(venv_python)"
  if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "Already running (PID $(cat "$PIDFILE"))"
    exit 0
  fi
  echo "Running from: $HERE"
  echo "Using PYTHON: $PY"
  echo "ENV: PYTHONPATH=$PYTHONPATH"
  nohup "$PY" app.py >> "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  echo "Started (PID $(cat "$PIDFILE")). Logs: $LOGFILE"
}

stop() {
  if [[ -f "$PIDFILE" ]]; then
    PID=$(cat "$PIDFILE" || true)
    if kill -0 "$PID" 2>/dev/null; then
      kill "$PID" || true
      sleep 1
      if kill -0 "$PID" 2>/dev/null; then kill -9 "$PID" || true; fi
      echo "Stopped PID $PID"
    else
      echo "Not running"
    fi
    rm -f "$PIDFILE"
  else
    echo "No PID file; attempting global kill"
    pkill -f "python.*app.py" || true
  fi
}

status() {
  if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "RUNNING (PID $(cat "$PIDFILE"))"
  else
    echo "STOPPED"
  fi
}

restart() { stop; start; }

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  setup) install_requirements_if_needed ;;
  doctor) doctor ;;
  *) echo "Usage: $0 {start|stop|restart|status|setup|doctor}" ; exit 1 ;;
esac
