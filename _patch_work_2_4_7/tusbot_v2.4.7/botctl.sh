#!/usr/bin/env bash
set -euo pipefail

# ----- Paths -----
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

APP="app.py"
PID_FILE="${PROJECT_DIR}/tustus_bot.pid"
LOG_FILE="${PROJECT_DIR}/bot.log"

VENV_DIR="${PROJECT_DIR}/.venv"
PY="${VENV_DIR}/bin/python"
PIP="${VENV_DIR}/bin/pip"

# ----- Helpers -----
ensure_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 not found. Please install Python 3.10+."
    exit 1
  fi
}

ensure_venv() {
  ensure_python
  if [[ ! -x "$PY" ]]; then
    echo "🔧 Creating virtualenv at: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  fi

  # Tools up-to-date
  "$PIP" -q install -U pip setuptools wheel

  # Install deps only if python-telegram-bot is missing
  if ! "$PY" - <<'PY' >/dev/null 2>&1
try:
    import telegram  # python-telegram-bot
except Exception:
    raise SystemExit(1)
PY
  then
    if [[ -f "requirements.txt" ]]; then
      echo "📦 Installing requirements.txt…"
      "$PIP" install -r requirements.txt
    else
      echo "📦 Installing core deps…"
      "$PIP" install "python-telegram-bot[job-queue]==20.7"
    fi
  fi
}

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

# ----- Commands -----
start() {
  ensure_venv
  if is_running; then
    echo "ℹ️  Already running (PID $(cat "$PID_FILE"))."
    exit 0
  fi
  echo "▶️  Starting bot (using $PY)…"
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
  echo "⏹  Stopping (PID $pid)…"
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

setup() {
  ensure_venv
  echo "✅ Environment ready at: $VENV_DIR"
  echo "   Python: $("$PY" -V)"
}

case "${1:-}" in
  start)   start ;;
  stop)    stop ;;
  restart) restart ;;
  status)  status ;;
  setup)   setup ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|setup}"
    exit 2
    ;;
esac
