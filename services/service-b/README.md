# Service B — internal forwarder

Internal only — bound to `127.0.0.1`, no Nginx route, blocked by UFW. Receives
requests from Service A and forwards them to Service C. Runs as a Django app
served by gunicorn on `127.0.0.1:3002`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check — returns service name, port, status. |
| GET | `/greet` | Forwards to Service C `/greet-c`, then returns `{"status":"forwarded","target":"service-c"}`. Returns `502` if the downstream call fails. |

Request/response shapes and log events: [`../../docs/API_CONTRACT.md`](../../docs/API_CONTRACT.md).

## How it talks to other services
Calls Service C at `SERVICE_C_URL` (default `http://service-c.internal:3003`),
propagating the `X-Request-ID` header.

## Run & test (from the repo root, venv active)

```bash
./scripts/run-local.sh
curl -s http://127.0.0.1:3002/health
curl -s http://127.0.0.1:3002/greet        # succeeds end-to-end when C is running
```

## Code
- `api/views.py` — request handlers
- `api/urls.py` — route table
- `service_b/` — Django settings / wsgi entry
