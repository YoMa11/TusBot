#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"
PID_FILE="$ROOT/app.pid"
LOG_FILE="$ROOT/bot.log"

case "$1" in
  setup)
    echo "[setup] creating venv at $VENV"
    python3 -m venv "$VENV"
    echo "[setup] installing requirements ..."
    "$PIP" install --upgrade pip wheel setuptools
    "$PIP" install -r "$ROOT/requirements.txt"
    echo "[setup] syntax check (python)"
    "$PY" - <<'PYCODE'
import os, sys, py_compile, pathlib
root = pathlib.Path(__file__).resolve().parent
errors = []
for p in root.glob("*.py"):
    try:
        py_compile.compile(str(p), doraise=True)
    except Exception as e:
        errors.append((p.name, str(e)))
if errors:
    print("Py syntax errors:", errors)
    sys.exit(1)
print("Py syntax OK")
PYCODE
    echo "[setup] syntax check (bash)"
    bash -n "$ROOT/botctl.sh"
    echo "[setup] chmod -R 777 ."
    chmod -R 777 "$ROOT"
    echo "[setup] done."
    ;;
  start)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Already running (PID $(cat "$PID_FILE"))."
      exit 0
    fi
    echo "Running from: $ROOT"
    echo "Using PYTHON: $PY"
    echo "ENV: PYTHONPATH=$ROOT"
    export PYTHONPATH="$ROOT"
    nohup "$PY" "$ROOT/app.py" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "Started (PID $(cat "$PID_FILE")). Logs: $LOG_FILE"
    ;;
  stop)
    if [ -f "$PID_FILE" ]; then
      kill "$(cat "$PID_FILE")" 2>/dev/null || true
      rm -f "$PID_FILE"
      echo "Stopped."
    else
      echo "Not running."
    fi
    ;;
  restart)
    "$0" stop
    sleep 1
    "$0" start
    ;;
  status)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "RUNNING (PID $(cat "$PID_FILE"))"
    else
      echo "NOT RUNNING"
      exit 1
    fi
    ;;
  doctor)
    echo "[doctor] Python: $("$PY" -V 2>&1)"
    echo "[doctor] python-telegram-bot: $("$PY" - <<'PYCODE'
import pkgutil
import importlib
m = importlib.import_module("telegram")
print(getattr(m, "__version__", "unknown"))
PYCODE
)"
    echo "[doctor] OK"
    ;;
  *)
    echo "Usage: $0 {setup|start|stop|restart|status|doctor}"
    exit 1
    ;;
esac
