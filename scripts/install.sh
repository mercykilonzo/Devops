#!/usr/bin/env bash
#
# install.sh — one-command deployment of the platform on an Ubuntu VM.
#
# Idempotent: safe to re-run. Must run as root (uses apt, systemd, /etc).
#
#   sudo ./scripts/install.sh
#
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run as root -> sudo $0" >&2
  exit 1
fi

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_DIR=/opt/platform
SVC_USER=platform

echo "==> [1/8] Installing prerequisites (nginx, curl, python3, django, gunicorn)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx curl ca-certificates python3
echo "    python3: $(python3 --version)   nginx: $(nginx -v 2>&1)"

# Django + gunicorn.
# Prefer distro packages: on Ubuntu 24.04+ the system Python is
# "externally managed" (PEP 668), so a bare `pip install` is refused.
# apt packages install into dist-packages, importable by /usr/bin/python3.
echo "    Installing Django and Gunicorn (apt, with pip fallback)..."
if apt-get install -y python3-django gunicorn python3-gunicorn; then
  :
else
  echo "    apt packages unavailable; falling back to pip"
  apt-get install -y python3-pip
  python3 -m pip install --break-system-packages "django>=4.2" "gunicorn>=21.0" \
    || python3 -m pip install "django>=4.2" "gunicorn>=21.0"
fi
python3 -c "import django, gunicorn; print('    django', django.get_version(), '| gunicorn import OK')"

echo "==> [2/8] Creating system user '$SVC_USER'..."
id -u "$SVC_USER" >/dev/null 2>&1 || \
  useradd --system --no-create-home --shell /usr/sbin/nologin "$SVC_USER"

echo "==> [3/8] Deploying application to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp -r "$REPO_DIR/services" "$INSTALL_DIR/"
cp -r "$REPO_DIR/scripts"  "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/scripts/"*.sh
chown -R "$SVC_USER:$SVC_USER" "$INSTALL_DIR"

echo "==> [4/8] Configuring service discovery (/etc/hosts)..."
bash "$REPO_DIR/scripts/setup-hosts.sh"

echo "==> [5/8] Installing systemd units..."
cp "$REPO_DIR/systemd/"*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable service-a.service service-b.service service-c.service

echo "==> [6/8] Installing Nginx reverse proxy..."
cp "$REPO_DIR/nginx/platform.conf" /etc/nginx/sites-available/platform.conf
ln -sf /etc/nginx/sites-available/platform.conf /etc/nginx/sites-enabled/platform.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "==> [7/8] Configuring firewall (UFW)..."
bash "$REPO_DIR/scripts/setup-firewall.sh" || echo "    (ufw step skipped/failed — non-fatal)"

echo "==> [8/8] Starting services (C, then B, then A)..."
systemctl restart service-c.service service-b.service service-a.service
sleep 2
systemctl --no-pager --lines=0 status service-a service-b service-c || true

echo
echo "Done. Verify with:"
echo "    sudo $INSTALL_DIR/scripts/healthcheck.sh"
echo "    sudo $INSTALL_DIR/scripts/smoke-test.sh"
