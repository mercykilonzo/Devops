# Service A — public entry point

**You own this service.** It is the only service exposed to the outside world
(through Nginx on port 80). It starts the request flow and receives the final
callback.

## What to implement

Edit **`api/views.py`** only. `/health` is already done as a reference.

1. **`GET /greet-service-b`** — call Service B and complete the flow.
2. **`POST /greeting-rcvd`** — receive Service C's callback.

Exact request/response shapes and log event names are in
[`../../docs/API_CONTRACT.md`](../../docs/API_CONTRACT.md).

## Run & test (from the repo root, venv active)

```bash
./scripts/run-local.sh
curl -s http://127.0.0.1:3001/health
curl -s -H "X-Request-ID: t1" http://127.0.0.1:3001/greet-service-b
```

Service A talks to Service B via `SERVICE_B_URL` (already set). You don't need
B and C finished to start — they return 501 until implemented — but the full
flow only succeeds once all three are done.

## Don't edit
`services/lib/`, the Django config in `service_a/`, `nginx/`, `systemd/`,
`scripts/` — those are shared. Coordinate with the team if you think one needs
to change.
