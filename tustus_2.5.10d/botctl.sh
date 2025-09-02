#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$APP_DIR/.venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"
LOG="$APP_DIR/bot.log"
PIDFILE="$APP_DIR/.bot.pid"
REQ="$APP_DIR/requirements.txt"
MAIN="$APP_DIR/app.py"

# אם לא רץ תחת bash – מריצים את עצמנו מחדש עם bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

ensure_venv() {
  if [ ! -d "$VENV" ]; then
    echo "[setup] creating venv at $VENV"
    python3 -m venv "$VENV"
  fi
  # shellcheck disable=SC1091
  . "$VENV/bin/activate"
  python -V >/dev/null
}

install_requirements() {
  echo "[setup] installing requirements ..."
  "$PIP" install --upgrade pip wheel setuptools >/dev/null
  if [ -f "$REQ" ]; then
    "$PIP" install -r "$REQ"
  fi
}

perm_all_777() {
  chmod -R 777 "$APP_DIR" || true
}

set_env() {
  # נועל טעינת מודולים רק לתיקיית הגרסה שרצה
  export PYTHONPATH="$APP_DIR"
}

doctor() {
  set_env
  ensure_venv
  echo
  echo "[doctor] Python: $("$PY" -V 2>&1)"
  PTB_VERSION="$("$PY" - <<'PYCODE'
import importlib, pkgutil
m = pkgutil.find_loader("telegram")
if not m:
    print("not installed")
else:
    try:
        mod = importlib.import_module("telegram")
        print(getattr(mod, "__version__", "unknown"))
    except Exception:
        print("unknown")
PYCODE
)"
  echo "[doctor] python-telegram-bot: $PTB_VERSION"
  echo "[doctor] OK"
}

is_running() {
  if [ -f "$PIDFILE" ]; then
    PID="$(cat "$PIDFILE" 2>/dev/null || true)"
    if [ -n "${PID:-}" ] && ps -p "$PID" >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

start() {
  set_env
  ensure_venv
  if is_running; then
    echo "ALREADY RUNNING (PID $(cat "$PIDFILE"))"
    exit 0
  fi
  echo
  echo "Running from: $APP_DIR"
  echo "Using PYTHON: $PY"
  echo "ENV: PYTHONPATH=$PYTHONPATH"
  nohup "$PY" "$MAIN" >>"$LOG" 2>&1 &
  echo $! > "$PIDFILE"
  echo "Started (PID $(cat "$PIDFILE")). Logs: $LOG"
}

stop() {
  if is_running; then
    PID="$(cat "$PIDFILE")"
    kill "$PID" 2>/dev/null || true
    # ממתין מעט לסגירה נקייה
    for i in 1 2 3 4 5; do
      if ps -p "$PID" >/dev/null 2>&1; then
        sleep 1
      else
        break
      fi
    done
    if ps -p "$PID" >/dev/null 2>&1; then
      kill -9 "$PID" 2>/dev/null || true
    fi
    rm -f "$PIDFILE"
    echo "STOPPED"
  else
    echo "NOT RUNNING"
  fi
}

restart() {
  stop || true
  start
}

status() {
  if is_running; then
    echo "RUNNING (PID $(cat "$PIDFILE"))"
  else
    echo "NOT RUNNING"
  fi
}

setup() {
  set_env
  ensure_venv
  install_requirements
  doctor
  perm_all_777
  echo "[setup] requirements installed."
}

usage() {
  cat <<EOF
Usage: ./botctl.sh <command>

Commands:
  setup      create venv, install requirements, set perms
  start      run app.py in background (logs to bot.log)
  stop       stop running process
  restart    restart process
  status     show process status
  doctor     print runtime versions (python, PTB)
EOF
}

CMD="${1:-}"
case "$CMD" in
  setup)   setup ;;
  start)   start ;;
  stop)    stop ;;
  restart) restart ;;
  status)  status ;;
  doctor)  doctor ;;
  ""|help|-h|--help) usage ;;
  *) echo "Unknown command: $CMD"; usage; exit 1;;
esac
