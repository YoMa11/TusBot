#!/bin/sh
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="$HERE/.venv"
PY="$VENV/bin/python"
PIDFILE="$HERE/app.pid"
LOGFILE="$HERE/bot.log"

case "${1:-help}" in
  setup)
    echo "[setup] creating venv at $VENV"
    python3 -m venv "$VENV"
    echo "[setup] installing requirements ..."
    "$VENV/bin/pip" install --upgrade pip wheel setuptools >/dev/null
    "$VENV/bin/pip" install -r "$HERE/requirements.txt"
    ;;
  start)
    echo "Running from: $HERE"
    echo "Using PYTHON: $PY"
    export PYTHONPATH="$HERE"
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "Already running (PID $(cat "$PIDFILE"))."
      exit 0
    fi
    nohup "$PY" "$HERE/app.py" >>"$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "Started (PID $(cat "$PIDFILE")). Logs: $LOGFILE"
    ;;
  stop)
    if [ -f "$PIDFILE" ]; then
      kill "$(cat "$PIDFILE")" 2>/dev/null || true
      rm -f "$PIDFILE"
      echo "Stopped."
    else
      echo "Not running."
    fi
    ;;
  restart)
    "$0" stop || true
    "$0" start
    ;;
  status)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "RUNNING (PID $(cat "$PIDFILE"))"
    else
      echo "NOT RUNNING"
    fi
    ;;
  doctor)
    export PYTHONPATH="$HERE"
    "$PY" - <<'PY'
import sys, importlib, pkg_resources
print("[doctor] Python:", sys.version.splitlines()[0])
for pkg in ["python-telegram-bot"]:
    try:
        print(f"[doctor] {pkg}:", pkg_resources.get_distribution(pkg).version)
    except Exception as e:
        print(f"[doctor] {pkg}: MISSING")
print("[doctor] OK")
PY
    ;;
  logs)
    tail -n 200 -f "$LOGFILE"
    ;;
  *)
    echo "usage: $0 {setup|start|stop|restart|status|doctor|logs}"
    exit 1
    ;;
esac
