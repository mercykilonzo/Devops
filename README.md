# Microservices Observability Lab

A three-service Django platform with a full MELT observability stack:
Prometheus · Grafana · Jaeger · Structured Logs · Alert Rules · Load Testing.

---

## Quick Start

```bash
git clone https://github.com/mercykilonzo/Devops.git
cd Devops
docker compose up --build
```

Wait ~30 seconds for all services to start, then verify:

```bash
curl http://localhost:8080/service-a/health
```

Expected:
```json
{"service": "service-a", "status": "ok", "port": 3001, "dependencies": {"service-b": "ok"}}
```

---

## Stack Access

| Service    | URL                        | Credentials       |
|------------|----------------------------|-------------------|
| Gateway    | http://localhost:8080           | —                 |
| Service A  | http://localhost:8080/service-a/ | via Nginx only    |
| Prometheus | http://localhost:9090       | —                 |
| Grafana    | http://localhost:3000       | admin / admin     |
| Jaeger UI  | http://localhost:16686      | —                 |

---

## How to Stop the Stack

```bash
docker compose down          # stop containers, keep volumes
docker compose down -v       # stop containers AND delete volumes (resets Prometheus data)
```

---

## How to View Metrics

**In Prometheus:**
1. Open http://localhost:9090
2. Click **Status → Targets** — all three services should show `UP`
3. Try these queries in the expression bar:
   ```promql
   http_requests_total
   rate(http_requests_total[1m])
   rate(http_errors_total[2m])
   histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
   up
   ```

**In Grafana:**
1. Open http://localhost:3000 (admin / admin)
2. Go to **Dashboards → Microservices Overview**
3. Panels: Service Up/Down · Request Rate · Error Rate · p95 Latency · Total Requests

**Raw metrics endpoint (per service):**
```bash
curl http://localhost:8080/service-a/metrics
# or direct (bypassing nginx):
# curl http://localhost:3001/metrics  (service-a exposed via port mapping)
```

---

## How to View Traces

1. Open Jaeger at http://localhost:16686
2. In the **Service** dropdown, select `service-a`
3. Click **Find Traces**
4. Click any trace to expand the span waterfall

**To generate a fresh trace:**
```bash
curl http://localhost:8080/service-a/greet-service-b
```

Expected trace path:
```
service-a  /greet-service-b
  └── service-b  /greet
        └── service-c  /greet-c
              └── service-a  /greeting-rcvd  (callback)
```

---

## How to View Logs

```bash
# All services together (follow mode)
docker compose logs -f

# One service
docker compose logs service-a
docker compose logs service-b
docker compose logs service-c

# Last 50 lines, follow
docker compose logs -f --tail=50 service-a
```

Each log line is structured JSON:
```json
{
  "timestamp": "2026-07-10T08:00:00.000000Z",
  "service": "service-a",
  "event": "flow_completed",
  "request_id": "abc-123",
  "trace_id": "abc-123",
  "method": "GET",
  "path": "/greet-service-b",
  "status": 200,
  "duration_ms": 34
}
```

---

## How to Run Load Tests

```bash
# Install ab first (if not already installed)
sudo apt install apache2-utils

# Individual scenarios
./scripts/load-test.sh normal    # 500 requests, 10 concurrent — baseline
./scripts/load-test.sh stress    # 2000 requests, 50 concurrent — watch latency climb
./scripts/load-test.sh failure   # 300 requests to /fail — triggers error alert

# All three in sequence
./scripts/load-test.sh all
```

Watch Grafana while the load test runs to see metrics change in real time.

---

## How to Trigger Failure

### Failure A: Service Down
```bash
# Stop a dependency
docker compose stop service-b

# Watch health check degrade
curl http://localhost:8080/service-a/health
# Returns: {"status": "degraded", "dependencies": {"service-b": "unreachable"}}

# Watch Prometheus target go down (within 15s)
# http://localhost:9090/targets

# Restore
docker compose start service-b
```

### Failure B: High Latency
```bash
# Hit the slow endpoint (2s artificial delay)
curl http://localhost:8080/service-a/slow

# Hammer it to trigger the HighLatency alert
for i in $(seq 1 20); do curl -s http://localhost:8080/service-a/slow & done; wait

# Check Jaeger — the /slow span will show ~2000ms duration
# Check Grafana — p95 latency panel will spike above 0.5s
```

### Failure C: High Error Rate
```bash
# Hit the fail endpoint
curl http://localhost:8080/service-a/fail

# Hammer it to trigger the HighErrorRate alert
./scripts/load-test.sh failure

# Check logs
docker compose logs service-a | grep fail_endpoint
```

---

## How to Confirm Alerts

**In Prometheus:**
1. Open http://localhost:9090/alerts
2. Alerts shown in three states: `inactive` (condition not met), `pending` (within `for` window), `firing` (alert active)

**Verify via API:**
```bash
curl -s http://localhost:9090/api/v1/rules | python3 -m json.tool | grep -E '"name"|"state"'
```

**The three alert rules:**

| Alert | Condition | For |
|-------|-----------|-----|
| ServiceDown | `up == 0` | 1 min |
| HighErrorRate | `rate(http_errors_total[2m]) > 0.1` | 2 min |
| HighLatency | `histogram_quantile(0.95, ...) > 0.5` | 2 min |

To reproduce each one, see *How to Trigger Failure* above.

---

## Running on a VM (production-style)

Besides Docker Compose, the same services run directly on an Ubuntu VM under
systemd + Nginx + UFW (this is the CI/CD deployment target). **One command does
everything:**

```bash
# on the VM:
git clone git@github.com:mercykilonzo/Devops.git
cd Devops
sudo ./scripts/install.sh          # idempotent; safe to re-run
```

`install.sh` installs dependencies, creates the `platform` user, deploys to
`/opt/platform`, writes `*.internal` service-discovery entries to `/etc/hosts`,
installs the three systemd units, configures Nginx, and locks UFW down to ports
**22 + 80**. A manual step-by-step equivalent is in [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

**Operating the services (systemd):**
```bash
systemctl status service-a service-b service-c
sudo systemctl restart service-b
sudo systemctl enable service-a service-b service-c   # auto-start on boot
sudo nginx -t && sudo systemctl reload nginx          # after a config change
```
Service A `Requires=`/`After=` B and C with a readiness gate (`wait-for-deps.sh`),
and every unit is `Restart=always`.

**Validate deployment + network isolation:**
```bash
sudo /opt/platform/scripts/healthcheck.sh    # all three respond
sudo /opt/platform/scripts/smoke-test.sh      # full flow + traced request id

sudo ss -ltnp | grep -E ':3001|:3002|:3003'  # all bound to 127.0.0.1 only
sudo ufw status verbose                        # 22 and 80 only
curl http://<VM_IP>:3002/health               # refused (B/C not public)
```

Mapping from Compose → VM: Compose DNS ↔ `/etc/hosts` names ·
`docker compose logs` ↔ `journalctl` · Docker network + single published port ↔
loopback bind + UFW.

---

## Repository Structure

```
.
├── docker-compose.yml          # Full stack: app + observability services
├── prometheus.yml              # Scrape config for all three services
├── alert-rules.yml             # ServiceDown, HighErrorRate, HighLatency
├── README.md                   # This file
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/        # Auto-provisions Prometheus data source
│   │   └── dashboards/         # Auto-loads dashboards on startup
│   └── dashboards/
│       └── services.json       # Microservices Overview dashboard
├── jaeger/
│   └── README.md               # Jaeger usage and demo walkthrough
├── nginx/
│   ├── platform.conf           # VM/bare-metal nginx config
│   └── nginx-docker.conf      # Docker Compose nginx config
├── scripts/
│   └── load-test.sh            # Normal / stress / failure scenarios
├── docs/
│   ├── architecture.md         # Request flow, telemetry flow, ASCII diagrams
│   ├── benchmark-report.md     # Load test results and lessons learned
│   ├── API_CONTRACT.md         # Endpoint reference
│   ├── RUNBOOK.md              # Operational runbook
│   └── TROUBLESHOOTING.md      # Common issues and fixes
└── services/
    ├── lib/                    # Shared: logger, http_client, util, metrics
    ├── service-a/              # Public entry point (Django + Gunicorn)
    ├── service-b/              # Internal forwarder
    └── service-c/              # Internal processor + callback
```

---

## MELT Signal Summary

| Signal  | Implementation | Where to view |
|---------|---------------|---------------|
| Metrics | `prometheus_client` — `/metrics` on each service | Prometheus, Grafana |
| Events  | Structured log events: `deployment_started`, `load_test_started`, `fail_endpoint_called` | `docker compose logs` |
| Logs    | JSON to stdout — `timestamp`, `service`, `event`, `request_id`, `trace_id`, `duration_ms` | `docker compose logs` |
| Traces  | `X-Request-ID` propagated A→B→C→A; OTLP spans to Jaeger | Jaeger UI |

---

## Controlled Failure Endpoints (LAB ONLY)

| Endpoint | Service | Effect | Triggers alert |
|----------|---------|--------|----------------|
| `/service-a/slow` | service-a | 2-second delay | HighLatency |
| `/service-a/fail` | service-a | Returns 500 | HighErrorRate |
| `docker compose stop service-b` | service-b | Takes service down | ServiceDown |

These endpoints are clearly marked as lab-only in the code.

---

## Operational Principle

> **Metrics tell us something is wrong.**
> **Logs explain what happened.**
> **Traces show where it happened.**
> **Events show what changed.**
> **Alerts call attention to the issue.**
