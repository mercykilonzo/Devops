# Service C — internal processor + callback

Internal only — bound to `127.0.0.1`, no Nginx route, blocked by UFW. Receives
requests from Service B, processes them, then calls back to Service A to signal
completion. Runs as a Django app served by gunicorn on `127.0.0.1:3003`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check — returns service name, port, status. |
| GET | `/greet-c` | Processes the request, POSTs a callback to Service A `/greeting-rcvd`, then returns `{"status":"processed","callback_sent":true}`. Returns `500` if the callback fails. |

Request/response shapes, the callback body, and log events:
[`../../docs/API_CONTRACT.md`](../../docs/API_CONTRACT.md).

## How it talks to other services
Calls back to Service A at `SERVICE_A_URL` (default
`http://service-a.internal:3001`) via `POST /greeting-rcvd`, propagating the
`X-Request-ID` header and a JSON body (`request_id`, `source_service`,
`message`, `timestamp`).

## Run & test (from the repo root, venv active)

```bash
./scripts/run-local.sh
curl -s http://127.0.0.1:3003/health
curl -s http://127.0.0.1:3003/greet-c      # succeeds when Service A is running
```

## Code
- `api/views.py` — request handlers
- `api/urls.py` — route table
- `service_c/` — Django settings / wsgi entry
