#!/usr/bin/env bash
#
# setup-hosts.sh — service discovery via /etc/hosts.
#
# Maps the *.internal service names to loopback. Because all three services run
# on the same VM and bind to 127.0.0.1, resolving the names to 127.0.0.1 lets
# them talk to each other by NAME (not hardcoded IP) while staying internal.
#
# Run as root (writes /etc/hosts).
#
set -euo pipefail

HOSTS=/etc/hosts
MARK="# platform-service-discovery"

add_entry() {
  local name="$1"
  if grep -qE "^[^#]*\b${name}\b" "$HOSTS"; then
    echo "    $name already present"
  else
    echo "127.0.0.1 ${name} ${MARK}" >> "$HOSTS"
    echo "    added 127.0.0.1 ${name}"
  fi
}

add_entry service-a.internal
add_entry service-b.internal
add_entry service-c.internal

echo "    /etc/hosts service-discovery entries:"
grep "$MARK" "$HOSTS" || true
