# Production-Style Service Environment

Three internal HTTP services (A, B, C) behind an Nginx reverse proxy, deployed
on a single Ubuntu VM and operated like a small production system:

- **Service discovery** by name (no hardcoded IPs)
- **Network isolation** — only the proxy is public; B and C are unreachable from outside
- **systemd** lifecycle management with dependency ordering and auto-restart
- **Structured JSON logging** to the system journal
- **End-to-end request tracing** with a single correlation id

Built in **Python + Django**, served by **gunicorn**. Reverse proxy: **Nginx**.
Firewall: **UFW**. Target OS: **Ubuntu 22.04 / 24.04**.

---

## Table of contents

1. [What it does](#what-it-does)
2. [Architecture](#architecture)
3. [API summary](#api-summary)
4. [Run it locally](#run-it-locally)
5. [Run it on a VM (production-style)](#run-it-on-a-vm-production-style)
6. [Running with Docker Compose](#running-with-docker-compose)
7. [Operating the services](#operating-the-services)
8. [Validating the system](#validating-the-system)
9. [Logs & request tracing](#logs--request-tracing)
10. [Repository layout](#repository-layout)
11. [Further documentation](#further-documentation)

---

## What it does

A single client request fans through all three services and back:

```
client → Nginx :80 /service-a/greet-service-b
       → Service A  GET  /greet-service-b
       → Service B  GET  /greet
       → Service C  GET  /greet-c
       → Service A  POST /greeting-rcvd      (callback from C)
       ← {"status":"success"} unwinds back to the client
```

The same `X-Request-ID` is carried through every hop, so one request can be
traced across all services in the logs.

| Service | Port | Public? | Role |
|---------|------|---------|------|
| **Service A** | 3001 | Yes (via Nginx) | Public entry point; starts the flow; receives the final callback |
| **Service B** | 3002 | No (internal) | Receives from A, forwards to C |
| **Service C** | 3003 | No (internal) | Processes, then calls back to A |
| **Nginx** | 80 | Yes | Reverse proxy — the only public entry point |

---

## Architecture

```
                    ┌───────────────────── Ubuntu VM ─────────────────────┐
 client ── :80 ───► │  Nginx  ──/service-a/──►  127.0.0.1:3001  Service A  │
                    │                                  │  GET /greet        │
   ✗ :3001/2/3      │                                  ▼                    │
 (loopback bind +   │                          127.0.0.1:3002  Service B    │
  UFW block)        │                                  │  GET /greet-c      │
                    │                                  ▼                    │
                    │                          127.0.0.1:3003  Service C    │
                    │   POST /greeting-rcvd  ◄─────────┘  (callback to A)    │
                    │                                                       │
                    │  discovery: /etc/hosts (*.internal → 127.0.0.1)        │
                    │  lifecycle: systemd     logs: journald (journalctl)    │
                    └───────────────────────────────────────────────────────┘
```

Each service is a small Django project served by gunicorn with **2 workers**.
Two workers matter: while Service A waits on B, Service C calls *back* into A —
a second worker handles that callback (one worker would deadlock the flow).

Full details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## API summary

Complete request/response shapes, the trace header, the log format, and error
codes are in **[`docs/API_CONTRACT.md`](docs/API_CONTRACT.md)**. At a glance:

| Service | Endpoint | Purpose |
|---------|----------|---------|
| A | `GET /health` | health check |
| A | `GET /greet-service-b` | start the flow; returns `{"status":"success",...}` |
| A | `POST /greeting-rcvd` | receive C's callback; returns `{"status":"received"}` |
| B | `GET /health` | health check |
| B | `GET /greet` | forward to C; returns `{"status":"forwarded",...}` |
| C | `GET /health` | health check |
| C | `GET /greet-c` | process + call back A; returns `{"status":"processed",...}` |

Publicly, everything is reached through Nginx under `/service-a/`
(e.g. `http://<host>/service-a/health`). B and C have no public route.

---

## Run it locally

For development on a laptop (macOS/Linux) — no Nginx, systemd, or VM needed.
All three services run on `127.0.0.1` and talk to each other directly.

```bash
git clone git@github.com:mercykilonzo/Devops.git
cd Devops

python3 -m venv .venv
source .venv/bin/activate
pip install -r services/service-a/requirements.txt   # Django + gunicorn

./scripts/run-local.sh        # starts A, B, C; Ctrl-C stops them
```

In a second terminal:

```bash
curl -s http://127.0.0.1:3001/health     # Service A
curl -s http://127.0.0.1:3002/health     # Service B
curl -s http://127.0.0.1:3003/health     # Service C

# full end-to-end flow:
curl -s -H "X-Request-ID: t1" http://127.0.0.1:3001/greet-service-b
# → {"request_id":"t1","status":"success","message":"Request completed successfully"}
```

The `run-local` terminal prints each service's JSON logs, so you can watch `t1`
travel A → B → C → A and complete.

> If you see `Address already in use`, a previous run is still up:
> `pkill -f gunicorn` then re-run. If you see `No module named django`, the venv
> isn't active or deps aren't installed — `source .venv/bin/activate` and
> `pip install -r services/service-a/requirements.txt`.

---

## Run it on a VM (production-style)

This deploys the full stack — gunicorn services under systemd, Nginx reverse
proxy, service discovery, and the UFW firewall — on an Ubuntu VM. **One command
does everything.**

### Prerequisites
- An Ubuntu 22.04 or 24.04 VM with `sudo` access and outbound internet (for `apt`)
- Inbound port **80** reachable (public entry) and **22** for SSH

### Deploy

```bash
# on the VM:
git clone git@github.com:mercykilonzo/Devops.git
cd Devops
sudo ./scripts/install.sh
```

`install.sh` is **idempotent** (safe to re-run) and performs every step:

| Step | What it does |
|------|--------------|
| 1 | Installs `nginx`, `curl`, `python3`, Django + gunicorn (via `apt`; pip fallback) |
| 2 | Creates the `platform` system user (no login shell) |
| 3 | Copies the app to `/opt/platform` and sets ownership |
| 4 | Writes service-discovery entries to `/etc/hosts` (`*.internal → 127.0.0.1`) |
| 5 | Installs + enables the three systemd units |
| 6 | Installs the Nginx site, runs `nginx -t`, reloads |
| 7 | Configures UFW (allows **22** and **80** only) |
| 8 | Starts the services in dependency order (C → B → A) |

### Verify the deployment

```bash
sudo /opt/platform/scripts/healthcheck.sh    # all three respond
sudo /opt/platform/scripts/smoke-test.sh     # full flow + request trace from journald
```

### Access it
From the VM (or any host that can reach port 80):

```bash
curl http://localhost/service-a/health
curl -H "X-Request-ID: demo-1" http://localhost/service-a/greet-service-b
```

### Redeploying after code changes
Re-run the installer (it re-copies `services/` and restarts):

```bash
cd Devops && git pull && sudo ./scripts/install.sh
```

### Removing it

```bash
sudo /opt/platform/scripts/uninstall.sh
```

> A manual, step-by-step version of the deploy (equivalent to `install.sh`) is
> in [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

---

## Running with Docker Compose

The same stack also runs under Docker Compose (Nginx + Service A/B/C). **Nginx is
the only service that publishes a host port (`8080`)**; B and C are reachable
only inside the Compose network. Requires Docker + the Compose plugin.

Validation evidence for all of the below is in
[`docs/CONTAINER_VALIDATION.md`](docs/CONTAINER_VALIDATION.md).

1. **Start the system**
   ```bash
   docker compose up --build -d
   docker compose ps        # nginx, service-a, service-b, service-c all "Up"
   ```
2. **Test the public route** (through Nginx)
   ```bash
   curl -i http://localhost:8080/service-a/health
   curl -i http://localhost:8080/service-a/greet-service-b   # full A→B→C→A flow
   ```
3. **Prove B and C are internal** (these should fail)
   ```bash
   curl --connect-timeout 3 http://localhost:3002/health     # refused
   curl --connect-timeout 3 http://localhost:3003/health     # refused
   ```
4. **View logs**
   ```bash
   docker compose logs            # all services
   docker compose logs service-a  # one service
   ```
5. **Stop / restart a service**
   ```bash
   docker compose stop service-b
   docker compose start service-b
   ```
6. **Shut everything down**
   ```bash
   docker compose down
   ```

How this maps from the VM version: `systemd` → Compose starts containers ·
`/etc/hosts` names → Compose DNS service names · `journalctl` →
`docker compose logs` · UFW + loopback bind → Docker network with only Nginx
publishing a port.

---

## Operating the services

All three run as standard systemd units, managed with normal commands:

```bash
# status
systemctl status service-a service-b service-c

# start / stop / restart
sudo systemctl start service-a        # pulls in B and C (Requires=)
sudo systemctl stop  service-a service-b service-c
sudo systemctl restart service-b

# enable / disable auto-start on boot
sudo systemctl enable  service-a service-b service-c
sudo systemctl disable service-a service-b service-c

# reload Nginx after a config change
sudo nginx -t && sudo systemctl reload nginx
```

**Dependencies & resilience:**
- Service A `Requires=` and starts `After=` B and C, and runs a readiness gate
  (`wait-for-deps.sh`) that waits for B's and C's `/health` before it boots.
- `Restart=always` — systemd revives any service that crashes.
- Because A hard-requires B and C, stopping B or C also stops A (fail-fast); the
  public endpoint then returns 502 until dependencies are back.

---

## Validating the system

```bash
# health (public path through Nginx + internal direct)
sudo /opt/platform/scripts/healthcheck.sh

# end-to-end flow with a traced request id
sudo /opt/platform/scripts/smoke-test.sh
```

**Network isolation** (these should behave as noted):

```bash
# services listen on loopback only:
sudo ss -ltnp | grep -E ':3001|:3002|:3003'      # all show 127.0.0.1:<port>

# firewall allows only SSH + HTTP:
sudo ufw status verbose                           # 22 and 80 only

# B and C are NOT reachable on the VM's external IP (only Nginp/:80 is):
curl http://<VM_IP>/service-a/health              # works (200)
curl http://<VM_IP>:3002/health                   # refused
curl http://<VM_IP>:3003/health                   # refused
```

---

## Logs & request tracing

Each service writes one JSON object per line to stdout, captured by the journal.

```bash
# one service
journalctl -u service-a -f

# all three together (best for tracing)
journalctl -t service-a -t service-b -t service-c -o cat

# Nginx access log (structured JSON)
sudo tail -f /var/log/nginx/platform_access.json
```

Trace a single request end-to-end:

```bash
RID="trace-$(date +%s)"
curl -s -H "X-Request-ID: $RID" http://localhost/service-a/greet-service-b
journalctl -t service-a -t service-b -t service-c -o cat | grep "$RID"
```

You'll see the id pass through `request_received` (A) → `request_forwarded` (B)
→ `callback_sent` (C) → `callback_received` (A) → `flow_completed` (A).

---

## Repository layout

```
Devops/
├── README.md                     # this file
├── services/
│   ├── lib/                      # shared helpers: logger, util, http_client
│   ├── service-a/                # public entry + callback receiver (Django)
│   ├── service-b/                # forwarder (Django)
│   └── service-c/                # processor + callback sender (Django)
├── nginx/platform.conf           # reverse proxy + JSON access log
├── systemd/                      # service-a/b/c.service units
├── scripts/                      # install, run-local, healthcheck, smoke-test, ...
└── docs/                         # API_CONTRACT, ARCHITECTURE, RUNBOOK, TROUBLESHOOTING
```

Each `services/service-*/` folder has its own README describing that service.

---

## Further documentation

- **[`docs/API_CONTRACT.md`](docs/API_CONTRACT.md)** — endpoints, request/response shapes, logging format, trace header, error codes
- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** — components, request flow, design decisions
- **[`docs/RUNBOOK.md`](docs/RUNBOOK.md)** — deploy/operate procedures, manual install
- **[`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)** — diagnosing common failures


# Running with Docker

> **Note:** The Docker implementation is available on the **`feature/docker`** branch. If you clone the repository from `main`, the Docker files (`docker-compose.yml`, `.dockerignore`, and the service Dockerfiles) will not be present.

## Features

The Docker implementation includes:

* Dockerized versions of Service A, Service B, and Service C
* Docker Compose configuration for running all services together
* Internal container networking for inter-service communication
* Health check endpoints
* Structured JSON logging
* Request ID propagation across all services
* Callback flow between services

## Prerequisites

Before running the project, install:

* Docker Engine
* Docker Compose

Verify your installation:

```bash
docker --version
docker compose version
```

## Clone the Repository

Clone the project and switch to the Docker feature branch:

```bash
git clone https://github.com/mercykilonzo/Devops.git
cd Devops
git checkout feature/docker
```

## Build the Containers

Build all Docker images:

```bash
docker compose build
```

Or build and start everything in one step:

```bash
docker compose up --build
```

## Start the Services

Run the application:

```bash
docker compose up
```

To run in detached mode:

```bash
docker compose up -d
```

## Verify the Containers

Ensure all services are running:

```bash
docker ps
```

Expected output should include:

* service-a
* service-b
* service-c

## Test the Services

### Service A Health Check

```bash
curl http://localhost:3001/health
```

Expected response:

```json
{
  "service": "service-a",
  "status": "healthy"
}
```

### Test the Complete Request Flow

```bash
curl -H "X-Request-ID: docker-test" \
http://localhost:3001/greet-service-b
```

Expected response:

```json
{
  "request_id": "docker-test",
  "status": "success",
  "message": "Request completed successfully"
}
```

## View Logs

Monitor logs from all services:

```bash
docker compose logs
```

View only the latest logs:

```bash
docker compose logs --tail=30
```

View logs for a specific service:

```bash
docker compose logs service-a
docker compose logs service-b
docker compose logs service-c
```

The logs demonstrate:

* Request received by Service A
* Forwarding to Service B
* Service B calling Service C
* Service C sending a callback to Service A
* Successful completion of the request

## Stop the Application

Stop all running containers:

```bash
docker compose down
```

To also remove associated volumes:

```bash
docker compose down -v
```

## Project Structure

```
.
├── docker-compose.yml
├── .dockerignore
└── services
    ├── service-a
    │   └── Dockerfile
    ├── service-b
    │   └── Dockerfile
    └── service-c
        └── Dockerfile
```

## Container CI/CD Deployment

### Latest deployed version
Commit:
`<fill in after first successful CI run>`

Image tag:
`sha-<fill in after first successful CI run>`

Images:
- `ushiadhiambo/devops-service-a:sha-<short-commit-hash>`
- `ushiadhiambo/devops-service-b:sha-<short-commit-hash>`
- `ushiadhiambo/devops-service-c:sha-<short-commit-hash>`

### Deploy
```bash
cp .env.example .env
export DOCKERHUB_USERNAME=ushiadhiambo
export APP_NAME=Devops
./scripts/deploy.sh sha-<short-commit-hash>
```

### Verify
```bash
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8080/service-a/health
```

### How to start the system
```bash
docker compose up --build -d
```

### How to test the public route
```bash
curl -s http://localhost:8090/service-a/health
```

### How to prove B and C are internal
```bash
curl -i --connect-timeout 3 http://localhost:3002/health
curl -i --connect-timeout 3 http://localhost:3003/health
```

### How to view logs
```bash
docker compose logs
docker compose logs service-a
docker compose logs service-b
docker compose logs service-c
```

### How to stop and restart a service
```bash
docker compose stop service-b
docker compose start service-b
```

### How to shut everything down
```bash
docker compose down
```

### Port note
Port 8080 is occupied by `lab-api.service` in the lab environment.
Nginx is mapped to port 8090 instead for local development.
All validation tests use port 8090.
