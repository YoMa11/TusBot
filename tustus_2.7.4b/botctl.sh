#!/usr/bin/env bash
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

PY="$HERE/.venv/bin/python"
PIP="$HERE/.venv/bin/pip"
APP="app.py"
LOG="$HERE/bot.log"
PIDFILE="$HERE/bot.pid"

function ensure_venv() {
  if [ ! -x "$PY" ]; then
    echo "[setup] creating venv at $HERE/.venv"
    python3 -m venv .venv
    . .venv/bin/activate
    python3 -m pip install --upgrade pip wheel setuptools
    python3 -m pip install -r requirements.txt
  else
    . .venv/bin/activate
  fi
}

case "$1" in
  setup)
    ensure_venv
    echo "[setup] requirements installed."
    ;;
  doctor)
    ensure_venv >/dev/null
    echo "[doctor] Python: $("$PY" -V)"
    echo "[doctor] python-telegram-bot: $("$PY" -c "import telegram; print(telegram.__version__)")"
    echo "[doctor] OK"
    ;;
  start)
    ensure_venv >/dev/null
    export PYTHONPATH="$HERE"
    chmod -R 777 "$HERE"
    echo "Running from: $HERE"
    echo "Using PYTHON: $PY"
    echo "ENV: PYTHONPATH=$PYTHONPATH"
    nohup "$PY" "$APP" >> "$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    echo "Started (PID $(cat "$PIDFILE")). Logs: $LOG"
    ;;
  stop)
    if [ -f "$PIDFILE" ]; then
      kill "$(cat "$PIDFILE")" || true
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
    if [ -f "$PIDFILE" ] && ps -p "$(cat "$PIDFILE")" >/dev/null 2>&1; then
      echo "RUNNING (PID $(cat "$PIDFILE"))"
    else
      echo "NOT RUNNING"
    fi
    ;;
  *)
    echo "Usage: $0 {setup|doctor|start|stop|restart|status}"
    exit 1
    ;;
esac
