#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="$ROOT/.venv/bin/python"
LOG="$ROOT/bot.log"
PIDFILE="$ROOT/.bot.pid"

cmd=${1:-help}

setup() {
  python3 -m venv "$ROOT/.venv"
  "$PY" -m pip install -U pip wheel setuptools
  "$PY" -m pip install -r "$ROOT/requirements.txt"
}

start() {
  export PYTHONPATH="$ROOT"
  nohup "$PY" "$ROOT/app.py" >>"$LOG" 2>&1 &
  echo $! > "$PIDFILE"
  echo "Started (PID $(cat "$PIDFILE")). Logs: $LOG"
}

stop() {
  if [[ -f "$PIDFILE" ]]; then
    kill -9 "$(cat "$PIDFILE")" || true
    rm -f "$PIDFILE"
    echo "Stopped."
  else
    echo "Not running."
  fi
}

status() {
  if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "RUNNING (PID $(cat "$PIDFILE"))"
  else
    echo "STOPPED"
  fi
}

doctor() {
  "$PY" - <<'PY'
import sys, pkgutil
print("[doctor] Python:", sys.version.splitlines()[0])
try:
    import telegram, telegram.ext
    print("[doctor] python-telegram-bot:", telegram.__version__)
except Exception as e:
    print("[doctor] PTB not found:", e)
print("[doctor] OK")
PY
}

case "$cmd" in
  setup) setup ;;
  start) start ;;
  stop) stop ;;
  status) status ;;
  doctor) doctor ;;
  *) echo "Usage: $0 {setup|start|stop|status|doctor}" ;;
esac
