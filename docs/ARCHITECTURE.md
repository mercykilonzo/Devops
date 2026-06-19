# Architecture

Three internal HTTP services behind an Nginx reverse proxy, deployed on one
Ubuntu VM with systemd + UFW. Each service is a small Django project served by
gunicorn (2 workers), sharing a framework-agnostic `lib/`.

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

## Why gunicorn with 2 workers

While Service A waits on Service B, Service C calls **back** into Service A
(`POST /greeting-rcvd`). With a single worker, A's only worker would be busy
waiting on B and could not accept C's callback → deadlock. Two workers let a
second worker handle the callback. **Service A must run with `--workers 2`.**

## Cross-cutting concerns (all provided in shared infra)

- **Service discovery:** `*.internal` names in `/etc/hosts` → `127.0.0.1`; URLs
  injected as env vars, never hardcoded.
- **Network security:** services bind to `127.0.0.1`; UFW allows only 22 + 80;
  Nginx exposes only `/service-a/`.
- **Lifecycle:** systemd units, enabled on boot, `Restart=always`; Service A
  `Requires`/`After` B and C with a health readiness gate.
- **Observability:** structured JSON logs to journald; `X-Request-ID` tracing.

See [`API_CONTRACT.md`](API_CONTRACT.md) for the per-service interface.
