# Service A — public entry point

The only service exposed to the outside world (through Nginx on port 80). It
starts the request flow, calls Service B, and receives the final callback from
Service C. Runs as a Django app served by gunicorn (2 workers) on
`127.0.0.1:3001`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check — returns service name, port, status. |
| GET | `/greet-service-b` | Starts the flow: calls Service B `/greet`, then returns `{"status":"success",...}`. Returns `502` if the downstream call fails. |
| POST | `/greeting-rcvd` | Receives Service C's callback and returns `{"status":"received"}`. |

Request/response shapes and log events: [`../../docs/API_CONTRACT.md`](../../docs/API_CONTRACT.md).

## How it talks to other services
Calls Service B at `SERVICE_B_URL` (default `http://service-b.internal:3002`),
propagating the `X-Request-ID` header. Service C calls back into
`/greeting-rcvd` — this is why Service A runs with ≥2 gunicorn workers, so the
callback is handled while the original request is still in flight.

## Run & test (from the repo root, venv active)

```bash
./scripts/run-local.sh
curl -s http://127.0.0.1:3001/health
curl -s -H "X-Request-ID: t1" http://127.0.0.1:3001/greet-service-b
```

## Code
- `api/views.py` — request handlers
- `api/urls.py` — route table
- `service_a/` — Django settings / wsgi entry
