#!/usr/bin/env bash
set -euo pipefail
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

PY="$DIR/.venv/bin/python"
PIP="$DIR/.venv/bin/pip"
LOG="$DIR/bot.log"
PIDFILE="$DIR/tustus.pid"

export PYTHONPATH="$DIR"

chmod -R 777 "$DIR" || true

case "${1:-}" in
  setup)
    echo "[setup] creating venv at $DIR/.venv"
    python3 -m venv .venv
    echo "[setup] installing requirements ..."
    "$PIP" install --upgrade pip wheel setuptools
    "$PIP" install -r "$DIR/requirements.txt"
    ;;
  start)
    echo ""
    echo "Running from: $DIR"
    echo "Using PYTHON: $PY"
    echo "ENV: PYTHONPATH=$PYTHONPATH"
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "Already running (PID $(cat "$PIDFILE"))"
      exit 0
    fi
    nohup "$PY" app.py >> "$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    echo "Started (PID $(cat "$PIDFILE")). Logs: $LOG"
    ;;
  stop)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      kill "$(cat "$PIDFILE")" || true
      rm -f "$PIDFILE"
      echo "Stopped."
    else
      echo "Not running."
    fi
    ;;
  restart)
    "$0" stop || true
    sleep 1
    "$0" start
    ;
  status)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "RUNNING (PID $(cat "$PIDFILE"))"
    else
      echo "NOT RUNNING"
      exit 1
    fi
    ;;
  atop)
    tail -n 200 -f "$LOG"
    ;;
  doctor)
    "$PY" - <<'PY'
import sys
print("[doctor] Python:", sys.version)
try:
    import telegram, telegram.ext as ext
    print("[doctor] python-telegram-bot:", getattr(ext, "__version__", "unknown"))
    print("[doctor] OK")
except Exception as e:
    print("[doctor] ERROR:", e)
    sys.exit(1)
PY
    ;;
  *)
    echo "Usage: $0 {setup|start|stop|restart|status|atop|doctor}"
    exit 1
    ;;
esac
