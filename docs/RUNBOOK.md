# Runbook — Operate the Platform

Operational procedures for deploying, running, and recovering the system.

## Prerequisites

- Ubuntu VM with `sudo` access
- Outbound internet (for `apt`) for first install
- Ports: 80 reachable from the reviewer; 22 for SSH

## Deploy

```bash
git clone <your-repo-url> devops && cd devops
sudo ./scripts/install.sh
sudo ./scripts/healthcheck.sh
sudo ./scripts/smoke-test.sh
```

### Manual deploy (equivalent to install.sh)

```bash
# 1. Packages (system + Python deps via apt; PEP 668-safe on Ubuntu 24.04)
sudo apt-get update && sudo apt-get install -y nginx curl python3 python3-django gunicorn python3-gunicorn

# 2. Service user
sudo useradd --system --no-create-home --shell /usr/sbin/nologin platform

# 3. App files
sudo mkdir -p /opt/platform
sudo cp -r services scripts /opt/platform/
sudo chmod +x /opt/platform/scripts/*.sh
sudo chown -R platform:platform /opt/platform

# 4. Service discovery
sudo ./scripts/setup-hosts.sh

# 5. systemd
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable service-a service-b service-c

# 6. Nginx
sudo cp nginx/platform.conf /etc/nginx/sites-available/platform.conf
sudo ln -sf /etc/nginx/sites-available/platform.conf /etc/nginx/sites-enabled/platform.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# 7. Firewall
sudo ./scripts/setup-firewall.sh

# 8. Start
sudo systemctl restart service-c service-b service-a
```

## Start / Stop / Restart

```bash
# Start everything (A pulls in B and C)
sudo systemctl start service-a

# Stop everything
sudo systemctl stop service-a service-b service-c

# Restart one service
sudo systemctl restart service-b

# Restart all in order
sudo systemctl restart service-c service-b service-a
```

## Verify health

```bash
sudo ./scripts/healthcheck.sh         # all three endpoints
curl http://localhost/service-a/health
```

## Run the end-to-end flow

```bash
sudo ./scripts/smoke-test.sh
# or manually:
curl -H "X-Request-ID: demo-1" http://localhost/service-a/greet-service-b
```

## View logs

```bash
journalctl -u service-a -f                       # follow one service
journalctl -t service-a -t service-b -t service-c -o cat   # all three
sudo tail -f /var/log/nginx/platform_access.json # nginx access (JSON)
```

## Reboot recovery test

```bash
sudo reboot
# after reconnecting:
systemctl status service-a service-b service-c   # all active
sudo ./scripts/healthcheck.sh                    # all healthy
```

## Common operational scenarios

### Stop a dependency and observe
```bash
sudo systemctl stop service-b
systemctl status service-a        # A is stopped too (Requires=)
sudo systemctl start service-b
sudo systemctl start service-a    # A waits for B+C health, then starts
```

### Roll back / remove
```bash
sudo ./scripts/uninstall.sh
```

## Demonstration checklist (maps to the rubric)

- [ ] Explain architecture (use `docs/ARCHITECTURE.md` diagram)
- [ ] `healthcheck.sh` — all services respond
- [ ] `smoke-test.sh` — full flow + single request_id across all logs
- [ ] Show `getent hosts service-b.internal` (discovery)
- [ ] Show `sudo nginx -T` `/service-a/` route; show no B/C route
- [ ] From outside: `curl http://<ip>:3002/health` fails (security)
- [ ] `systemctl status` / `restart` / kill-and-watch-restart (lifecycle)
- [ ] `journalctl ... | grep <request_id>` (logging + tracing)
- [ ] Stop Service B → explain `Requires=` behavior and 502 degradation
- [ ] `sudo reboot` → everything comes back (reboot recovery)
