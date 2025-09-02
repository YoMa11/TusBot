#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

APP="app.py"
PID_FILE="${PROJECT_DIR}/tustus_bot.pid"
LOG_FILE="${PROJECT_DIR}/bot.log"

VENV_DIR="${PROJECT_DIR}/.venv"
VENV_PY="${VENV_DIR}/bin/python3"

if [[ -x "$VENV_PY" ]]; then
  PY="$VENV_PY"
else
  # Fallback to system python3 if venv doesn't exist
  if command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
    echo "⚠️  Using system python: ${PY} (no .venv found)"
  else
    echo "❌ python3 not found. Please install Python 3.10+."
    exit 1
  fi
fi

is_running() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "${pid}" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

start() {
  if is_running; then
    echo "ℹ️  Already running (PID $(cat "$PID_FILE"))."
    exit 0
  fi
  echo "▶️  Starting bot..."
  nohup "$PY" "$APP" >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  sleep 0.5
  if is_running; then
    echo "✅ Started (PID $(cat "$PID_FILE")). Logs: $LOG_FILE"
  else
    echo "❌ Failed to start. Check $LOG_FILE"
    exit 1
  fi
}

stop() {
  if ! is_running; then
    echo "ℹ️  Not running."
    exit 0
  fi
  local pid
  pid="$(cat "$PID_FILE")"
  echo "⏹  Stopping (PID $pid)..."
  kill "$pid" || true
  # graceful wait
  for i in {1..20}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      break
    fi
    sleep 0.2
  done
  if kill -0 "$pid" 2>/dev/null; then
    echo "⚠️  Force kill."
    kill -9 "$pid" || true
  fi
  rm -f "$PID_FILE"
  echo "✅ Stopped."
}

restart() {
  stop || true
  start
}

status() {
  if is_running; then
    echo "🟢 Running (PID $(cat "$PID_FILE"))."
  else
    echo "🔴 Not running."
  fi
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 2
    ;;
esac
