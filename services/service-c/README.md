# Service C — internal processor + callback

**You own this service.** It is internal only (bound to `127.0.0.1`, no Nginx
route, blocked by UFW). It receives requests from Service B, then calls back to
Service A to signal completion.

## What to implement

Edit **`api/views.py`** only. `/health` is already done as a reference.

1. **`GET /greet-c`** — process the request, then `POST` a callback to Service
   A's `/greeting-rcvd` (propagating `X-Request-ID`), and return the contracted
   JSON.

Exact request/response shapes, the callback body, and log event names are in
[`../../docs/API_CONTRACT.md`](../../docs/API_CONTRACT.md).

## Run & test (from the repo root, venv active)

```bash
./scripts/run-local.sh
curl -s http://127.0.0.1:3003/health
curl -s http://127.0.0.1:3003/greet-c       # once implemented
```

Service C talks back to Service A via `SERVICE_A_URL` (already set).

## Don't edit
`services/lib/`, the Django config in `service_c/`, `nginx/`, `systemd/`,
`scripts/` — those are shared. Coordinate with the team if you think one needs
to change.
