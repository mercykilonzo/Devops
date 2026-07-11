# Architecture

## Service Architecture

Three Django/Gunicorn microservices sit behind an Nginx gateway.
Service B and C are internal-only; only Service A is reachable from outside.

```
Client / Load Test
      |
      v
   Nginx :80
      |
      v (only /service-a/* is routed)
  Service A :3001 ──────────────────────────────────────┐
      |                                                   |
      | GET /greet-service-b                              |
      v                                                   |
  Service B :3002                                         |
      |                                                   |
      | GET /greet-c                                      |
      v                                                   |
  Service C :3003                                         |
      |                                                   |
      | POST /greeting-rcvd (callback)                    |
      └───────────────────────────────────────────────────┘
```

### Why gunicorn with 2 workers

While Service A waits on Service B, Service C calls **back** into Service A
(`POST /greeting-rcvd`). With a single worker, A's only worker would be busy
waiting on B and could not accept C's callback → deadlock. Two workers let a
second worker handle the callback. **Service A must run with `--workers 2`.**

## Request Flow

1. Client sends `GET /service-a/greet-service-b` to Nginx on port 80.
2. Nginx strips the `/service-a/` prefix and forwards to Service A on port 3001.
   Nginx generates or propagates `X-Request-ID`.
3. Service A calls Service B `GET /greet`, forwarding `X-Request-ID`.
4. Service B calls Service C `GET /greet-c`, forwarding `X-Request-ID`.
5. Service C processes the request and fires a `POST /greeting-rcvd` callback to Service A.
6. Service A responds 200 to the original client.

## Telemetry Flow

```
Service A ──┐
Service B ──┼──► /metrics ──► Prometheus (scrape every 15s) ──► Grafana
Service C ──┘

Service A ──┐
Service B ──┼──► OTLP HTTP :4318 ──► Jaeger (all-in-one)
Service C ──┘

Service A ──┐
Service B ──┼──► stdout (structured JSON) ──► docker compose logs
Service C ──┘
```

## Metrics Collection Flow

1. Each service exposes `GET /metrics` returning Prometheus text format.
2. `prometheus.yml` defines scrape jobs for each service using Docker Compose service names.
3. Prometheus scrapes every 15 seconds and stores metrics in a named volume (`prometheus-data`).
4. Grafana reads from Prometheus via the provisioned data source.

## Tracing Flow

1. Each service receives `X-Request-ID` from the inbound request (or generates one).
2. The ID is propagated downstream via the same header.
3. Each service emits OTLP spans to `http://jaeger:4318/v1/traces`.
4. Jaeger assembles spans into a trace using the shared trace/request ID.
5. The full A → B → C → A journey is visible in the Jaeger UI.

## Logging Flow

1. Every service writes one JSON line to stdout per significant event.
2. Each log line includes `timestamp`, `service`, `event`, `request_id`, and `trace_id`.
3. Docker captures stdout into container logs.
4. Access: `docker compose logs service-a` or `docker compose logs -f --tail=50`.

## Alerting Flow

1. Alert rules are defined in `alert-rules.yml` and loaded by Prometheus at startup.
2. Prometheus evaluates rules every 15 seconds.
3. When a condition is true for the `for` duration, an alert fires.
4. Alerts are visible at `http://localhost:9090/alerts`.
5. (Optional) Alertmanager can route alerts to Slack/email — see Alertmanager docs.

## Deployment (VM, production-style)

The Docker Compose stack above is the lab topology. The same services also run
directly on a single Ubuntu VM under systemd + UFW (the CI/CD deployment target):

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

Cross-cutting concerns (VM deployment):

- **Service discovery:** `*.internal` names in `/etc/hosts` → `127.0.0.1`; URLs
  injected as env vars, never hardcoded.
- **Network security:** services bind to `127.0.0.1`; UFW allows only 22 + 80;
  Nginx exposes only `/service-a/`.
- **Lifecycle:** systemd units, enabled on boot, `Restart=always`; Service A
  `Requires`/`After` B and C with a health readiness gate.
- **Observability:** structured JSON logs to journald; `X-Request-ID` tracing.

See [`API_CONTRACT.md`](API_CONTRACT.md) for the per-service interface.

## Known Limitations

- Jaeger uses in-memory storage. Traces are lost on container restart.
- Prometheus retention defaults to 15 days. Use `--storage.tsdb.retention.time` to change.
- `X-Request-ID` is used for log correlation. Distributed tracing uses W3C trace
  context (`traceparent`), propagated automatically by the OpenTelemetry urllib
  instrumentation, so spans from all services link into a single trace in Jaeger.
- No TLS. This is a lab stack, not a production deployment.
