#!/usr/bin/env bash
#
# run-local.sh — developer mode (no systemd, no Nginx, no /etc/hosts changes).
#
# Starts all three Django services on 127.0.0.1 using plain localhost URLs so
# you can test the full flow on a laptop (macOS/Linux). Ctrl-C stops everything.
#
# Requires:  pip install django gunicorn   (or: pip install -r services/service-a/requirements.txt)
#
#   ./scripts/run-local.sh
#   # then, in another terminal:
#   curl -s http://127.0.0.1:3001/greet-service-b
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$(command -v python3 || command -v python)"

export PYTHONUNBUFFERED=1
export BIND_ADDR=127.0.0.1
export SERVICE_A_URL=http://127.0.0.1:3001
export SERVICE_B_URL=http://127.0.0.1:3002
export SERVICE_C_URL=http://127.0.0.1:3003

pids=()
PORT=3003 DJANGO_SETTINGS_MODULE=service_c.settings \
  "$PY" -m gunicorn service_c.wsgi:application \
  --chdir "$ROOT/services/service-c" --bind 127.0.0.1:3003 --workers 2 \
  --log-level warning & pids+=($!)

PORT=3002 DJANGO_SETTINGS_MODULE=service_b.settings \
  "$PY" -m gunicorn service_b.wsgi:application \
  --chdir "$ROOT/services/service-b" --bind 127.0.0.1:3002 --workers 2 \
  --log-level warning & pids+=($!)

PORT=3001 DJANGO_SETTINGS_MODULE=service_a.settings \
  "$PY" -m gunicorn service_a.wsgi:application \
  --chdir "$ROOT/services/service-a" --bind 127.0.0.1:3001 --workers 2 \
  --log-level warning & pids+=($!)

echo "Started service-c(:3003), service-b(:3002), service-a(:3001) (PIDs: ${pids[*]})"
echo "Try:  curl -s http://127.0.0.1:3001/greet-service-b"
echo "Ctrl-C to stop."

trap 'echo; echo "Stopping..."; kill "${pids[@]}" 2>/dev/null || true; wait 2>/dev/null || true' INT TERM
wait
