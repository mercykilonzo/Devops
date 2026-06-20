#!/usr/bin/env bash
#
# setup-firewall.sh — UFW rules (network security, defense in depth).
#
# The services already bind to 127.0.0.1 so 3001/3002/3003 are not reachable
# from other hosts. UFW is the second layer: only SSH (22) and the public
# proxy (80) are allowed inbound. The service ports are never opened.
#
# Run as root.
#
set -euo pipefail

if ! command -v ufw >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get install -y ufw
fi

ufw --force reset
ufw default deny incoming
ufw default allow outgoing

ufw allow 22/tcp   comment 'SSH'
ufw allow 80/tcp   comment 'Nginx public entry (Service A)'
# Ports 3001/3002/3003 are intentionally NOT opened — internal only.

ufw --force enable
echo
ufw status verbose
