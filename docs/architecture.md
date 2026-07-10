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

## Known Limitations

- Jaeger uses in-memory storage. Traces are lost on container restart.
- Prometheus retention defaults to 15 days. Use `--storage.tsdb.retention.time` to change.
- Services use `X-Request-ID` for correlation, not a full OpenTelemetry trace context.
  Spans are emitted but correlation across services in Jaeger relies on the request ID.
- No TLS. This is a lab stack, not a production deployment.
