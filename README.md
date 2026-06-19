# Devops — Production-Style Service Environment

A team project: three internal HTTP services (A, B, C) behind an Nginx reverse
proxy, with service discovery, network isolation, systemd lifecycle management,
structured JSON logging, and end-to-end request tracing. Built in **Python +
Django** (served by **gunicorn**) on **Ubuntu**.

Each service is built by a different teammate against a shared contract.

## Start here

1. **[`docs/API_CONTRACT.md`](docs/API_CONTRACT.md)** — the interface every
   service must implement (read this first).
2. **[`CONTRIBUTING.md`](CONTRIBUTING.md)** — who owns what, git workflow, setup.
3. **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** — how the pieces fit.

## The request flow

```
client → Nginx :80 /service-a/... → Service A → Service B → Service C → Service A (callback) → success
```

## Quick start (local, no VM)

```bash
git clone git@github.com:mercykilonzo/Devops.git && cd Devops
python3 -m venv .venv && source .venv/bin/activate
pip install -r services/service-a/requirements.txt
./scripts/run-local.sh
# new terminal:
curl -s http://127.0.0.1:3001/health     # service A
curl -s http://127.0.0.1:3002/health     # service B
curl -s http://127.0.0.1:3003/health     # service C
```

`/health` works for all three immediately. The full `/greet-service-b` flow
succeeds once each owner implements their service's endpoint (stubs return 501).

## Deploy on the Ubuntu VM (shared infra — done for you)

```bash
sudo ./scripts/install.sh          # apt + django/gunicorn, systemd, nginx, ufw
sudo ./scripts/healthcheck.sh
sudo ./scripts/smoke-test.sh
```

## Layout

```
services/
  lib/            shared helpers — DO NOT EDIT (logger, util, http_client)
  service-a/      OWNER 1 — public entry + callback receiver  (Django stub)
  service-b/      OWNER 2 — forwarder                          (Django stub)
  service-c/      OWNER 3 — processor + callback sender        (Django stub)
nginx/            reverse proxy config        (shared)
systemd/          unit files                  (shared)
scripts/          install / run-local / healthcheck / smoke-test / ...  (shared)
docs/             API_CONTRACT, ARCHITECTURE
```

Each service folder has its own README describing exactly what to implement.
