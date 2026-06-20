#!/usr/bin/env bash
#
# wait-for-deps.sh — readiness gate for Service A (used as ExecStartPre).
#
# Service A must not become operational until Service B and Service C answer
# their /health endpoints. Polls both until ready or until DEP_WAIT_TIMEOUT
# seconds elapse, in which case it exits non-zero and systemd retries the unit.
#
set -euo pipefail

B_URL="${SERVICE_B_URL:-http://service-b.internal:3002}"
C_URL="${SERVICE_C_URL:-http://service-c.internal:3003}"
TIMEOUT="${DEP_WAIT_TIMEOUT:-30}"

deadline=$(( $(date +%s) + TIMEOUT ))

for dep in "$B_URL/health" "$C_URL/health"; do
  echo "wait-for-deps: checking $dep"
  until curl -fsS --max-time 2 "$dep" >/dev/null 2>&1; do
    if [ "$(date +%s)" -ge "$deadline" ]; then
      echo "wait-for-deps: dependency NOT ready within ${TIMEOUT}s -> $dep" >&2
      exit 1
    fi
    sleep 1
  done
  echo "wait-for-deps: ready -> $dep"
done

echo "wait-for-deps: all dependencies healthy"
