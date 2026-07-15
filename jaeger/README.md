# Jaeger — Distributed Tracing

## What Jaeger does

Jaeger collects distributed traces from each service and lets you follow a single
request as it travels through service-a → service-b → service-c → service-a.

Prometheus can tell you *that* latency increased. Jaeger tells you *where*.

## How tracing works in this stack

Each service propagates the `X-Request-ID` header across service calls. Jaeger
receives spans via OTLP HTTP on port 4318. Every span records:

- Service name
- Endpoint (route)
- Duration
- Status / error state

## Accessing Jaeger

Open http://localhost:16686 after `docker compose up`.

## Demo trace walkthrough

1. Send a request through the gateway:
   ```
   curl -v http://localhost/service-a/greet-service-b
   ```

2. Open Jaeger UI → select service `service-a` → click Find Traces.

3. Click the trace. You should see the full journey:
   ```
   service-a /greet-service-b
     └── service-b /greet
           └── service-c /greet-c
                 └── service-a /greeting-rcvd  (callback)
   ```

4. To demonstrate a slow span:
   ```
   curl http://localhost/service-a/slow
   ```
   In Jaeger, the span for `/slow` will show ~2000ms duration.

5. To demonstrate a failed span:
   ```
   curl http://localhost/service-a/fail
   ```
   The span will be marked as an error.

## Configuration

Jaeger runs as `all-in-one` (single container, in-memory storage).
This is appropriate for a lab — not for production where a persistent backend
(Elasticsearch or Cassandra) would be required.

Port mappings:
- `16686` — Jaeger UI
- `4318`  — OTLP HTTP receiver (used by services)
- `6831`  — Jaeger compact Thrift (UDP, legacy agents)
