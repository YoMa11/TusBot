#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

PY="$PWD/.venv/bin/python"
APP="app.py"
PIDFILE=".bot.pid"

function setup() {
  echo "[setup] creating venv at $PWD/.venv"
  python3 -m venv .venv
  echo "[setup] installing requirements ..."
  "$PY" -m pip install -U pip wheel setuptools >/dev/null
  "$PY" -m pip install -r requirements.txt
  echo "[setup] requirements installed."
}

function start() {
  echo ""
  echo "Running from: $PWD"
  echo "Using PYTHON: $PY"
  export PYTHONPATH="$PWD"
  nohup "$PY" "$APP" > bot.out 2>&1 &
  echo $! > "$PIDFILE"
  echo "Started (PID $(cat $PIDFILE)). Logs: $PWD/bot.log"
}

function stop() {
  if [ -f "$PIDFILE" ]; then
    kill -9 "$(cat "$PIDFILE")" 2>/dev/null || true
    rm -f "$PIDFILE"
    echo "Stopped."
  else
    echo "Not running."
  fi
}

function status() {
  if [ -f "$PIDFILE" ] && ps -p "$(cat "$PIDFILE")" >/dev/null 2>&1; then
    echo "RUNNING (PID $(cat "$PIDFILE"))"
  else
    echo "NOT RUNNING"
  fi
}

function restart() { stop; start; }

function doctor() {
  echo "[doctor] Python: $("$PY" -V 2>/dev/null || python3 -V)"
  echo "[doctor] python-telegram-bot: $("$PY" -c 'import telegram;print(getattr(telegram,"__version__", "unknown"))' 2>/dev/null || echo unknown)"
  echo "[doctor] OK"
}

case "$1" in
  setup) setup ;;
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  doctor) doctor ;;
  *) echo "Usage: $0 {setup|start|stop|restart|status|doctor}" ;;
esac
