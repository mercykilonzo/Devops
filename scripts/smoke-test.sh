#!/usr/bin/env bash
#
# smoke-test.sh — exercise the full A -> B -> C -> A flow with a known request
# id, then reconstruct the request journey from the journals.
#
set -euo pipefail

RID="smoke-$(date +%s)"
echo "==> Triggering full flow with X-Request-ID=$RID"
echo "    GET http://localhost/service-a/greet-service-b"
echo
curl -fsS -H "X-Request-ID: $RID" http://localhost/service-a/greet-service-b
echo
echo

echo "==> Request journey for $RID (from journald):"
if command -v journalctl >/dev/null 2>&1; then
  journalctl -t service-a -t service-b -t service-c --since "2 min ago" -o cat 2>/dev/null \
    | grep "$RID" || echo "    (no journald entries found — are you running under systemd?)"
else
  echo "    journalctl not available (not running under systemd / not on the VM)."
fi
