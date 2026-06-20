#!/usr/bin/env bash
#
# uninstall.sh — remove the platform from the VM. Run as root.
#
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run as root -> sudo $0" >&2
  exit 1
fi

echo "==> Stopping and disabling services..."
systemctl disable --now service-a.service service-b.service service-c.service 2>/dev/null || true

echo "==> Removing systemd units..."
rm -f /etc/systemd/system/service-a.service \
      /etc/systemd/system/service-b.service \
      /etc/systemd/system/service-c.service
systemctl daemon-reload

echo "==> Removing Nginx config..."
rm -f /etc/nginx/sites-enabled/platform.conf /etc/nginx/sites-available/platform.conf
nginx -t 2>/dev/null && systemctl reload nginx || true

echo "==> Removing service-discovery entries from /etc/hosts..."
sed -i '/# platform-service-discovery/d' /etc/hosts

echo "==> Removing application files..."
rm -rf /opt/platform

echo "Done. Left intact: the 'platform' user and UFW rules (remove manually if desired)."
