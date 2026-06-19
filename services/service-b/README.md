# Service B — internal forwarder

**You own this service.** It is internal only (bound to `127.0.0.1`, no Nginx
route, blocked by UFW). It receives requests from Service A and forwards them to
Service C.

## What to implement

Edit **`api/views.py`** only. `/health` is already done as a reference.

1. **`GET /greet`** — forward to Service C's `/greet-c`, propagating the
   `X-Request-ID`, and return the contracted JSON.

Exact request/response shapes and log event names are in
[`../../docs/API_CONTRACT.md`](../../docs/API_CONTRACT.md).

## Run & test (from the repo root, venv active)

```bash
./scripts/run-local.sh
curl -s http://127.0.0.1:3002/health
curl -s http://127.0.0.1:3002/greet        # once implemented (needs C for full success)
```

Service B talks to Service C via `SERVICE_C_URL` (already set).

## Don't edit
`services/lib/`, the Django config in `service_b/`, `nginx/`, `systemd/`,
`scripts/` — those are shared. Coordinate with the team if you think one needs
to change.
