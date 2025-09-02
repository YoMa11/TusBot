#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"
PIDFILE="$ROOT/bot.pid"
LOG="$ROOT/bot.log"

chmod -R 777 "$ROOT" || true

case "$1" in
  setup)
    echo "[setup] creating venv at $VENV"
    python3 -m venv "$VENV"
    echo "[setup] installing requirements ..."
    "$PIP" install -U pip wheel setuptools >/dev/null
    "$PIP" install -r "$ROOT/requirements.txt"
    chmod -R 777 "$ROOT"
    ;;
  start)
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
      echo "Already running (PID $(cat "$PIDFILE"))"
      exit 0
    fi
    echo "Running from: $ROOT"
    echo "Using PYTHON: $PY"
    export PYTHONPATH="$ROOT"
    nohup "$PY" "$ROOT/app.py" >"$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    chmod -R 777 "$ROOT"
    echo "Started (PID $(cat "$PIDFILE")). Logs: $LOG"
    ;;
  stop)
    if [ -f "$PIDFILE" ]; then
      PID=$(cat "$PIDFILE")
      if kill -0 $PID 2>/dev/null; then
        kill $PID || true
      fi
      rm -f "$PIDFILE"
      echo "Stopped"
    else
      echo "Not running"
    fi
    ;;
  restart)
    "$0" stop || true
    "$0" start
    ;;
  status)
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
      echo "RUNNING (PID $(cat "$PIDFILE"))"
    else
      echo "STOPPED"
    fi
    ;;
  doctor)
    "$PY" -V
    "$PY" -c "import telegram; import telegram.ext; import sys; print('[doctor] PTB:', telegram.__version__)"
    ;;
  *)
    echo "Usage: $0 {setup|start|stop|restart|status|doctor}"
    exit 1
    ;;
esac
