#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
export PYTHONPATH="$PWD"
VENV="$HERE/.venv"
PIDFILE="$HERE/bot.pid"
LOGFILE="$HERE/bot.log"
PY="${PY:-python3}"
if [[ -x "$VENV/bin/python" ]]; then PY="$VENV/bin/python"; fi

chmod -R 777 "$HERE" || true

start() {
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
  *) echo "Usage: $0 {start|stop|restart|status}" ; exit 1 ;;
esac
