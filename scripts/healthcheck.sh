#!/usr/bin/env bash
#
# healthcheck.sh — verify every service responds. Exits non-zero on any failure.
#
set -euo pipefail

fail=0
check() {
  local label="$1" url="$2"
  printf '  %-34s ' "$label"
  if out=$(curl -fsS --max-time 3 "$url" 2>/dev/null); then
    echo "OK  -> $out"
  else
    echo "FAIL ($url)"
    fail=1
  fi
}

echo "== Public path (through Nginx, port 80) =="
check "GET /service-a/health"        "http://localhost/service-a/health"

echo "== Internal services (direct, on-VM only) =="
check "GET service-b.internal:3002"  "http://service-b.internal:3002/health"
check "GET service-c.internal:3003"  "http://service-c.internal:3003/health"

echo
if [ "$fail" -eq 0 ]; then
  echo "All services healthy."
else
  echo "One or more checks FAILED. See TROUBLESHOOTING.md."
  exit 1
fi
