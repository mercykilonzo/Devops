# API & Logging Contract  ⭐ single source of truth

Every service is built by a different person, so this contract is what makes
them fit together at merge time. **Do not change it without telling the team.**

## Services, ports, discovery

| Service | Port | Public? | Discovery name |
|---------|------|---------|----------------|
| Service A | 3001 | Yes (via Nginx `/service-a/`) | `service-a.internal` |
| Service B | 3002 | No (internal) | `service-b.internal` |
| Service C | 3003 | No (internal) | `service-c.internal` |

- Services call each other by **name**, never by IP, using the env vars
  `SERVICE_A_URL`, `SERVICE_B_URL`, `SERVICE_C_URL` (already set in the systemd
  units and `run-local.sh`).
- All services bind to `127.0.0.1`.

## The flow

```
client → Nginx :80 /service-a/greet-service-b
      → A  GET  /greet-service-b
      → B  GET  /greet
      → C  GET  /greet-c
      → A  POST /greeting-rcvd      (callback from C)
      ← success unwinds back to the client
```

## Endpoints (build exactly these)

### Service A  (owner: Person 1)
| Method | Path | Purpose | Success response (200) |
|--------|------|---------|------------------------|
| GET | `/health` | health check | `{"service":"service-a","status":"healthy","port":3001,"message":"..."}` |
| GET | `/greet-service-b` | call B, complete the flow | `{"request_id":"<id>","status":"success","message":"Request completed successfully"}` |
| POST | `/greeting-rcvd` | receive C's callback | `{"status":"received"}` |

`/greeting-rcvd` receives this JSON body from C:
```json
{"request_id":"<id>","source_service":"service-c","message":"Greeting processed","timestamp":"<iso8601>"}
```

### Service B  (owner: Person 2)
| Method | Path | Purpose | Success response (200) |
|--------|------|---------|------------------------|
| GET | `/health` | health check | `{"service":"service-b","status":"healthy","port":3002,"message":"..."}` |
| GET | `/greet` | forward to C `/greet-c` | `{"request_id":"<id>","status":"forwarded","target":"service-c"}` |

### Service C  (owner: Person 3)
| Method | Path | Purpose | Success response (200) |
|--------|------|---------|------------------------|
| GET | `/health` | health check | `{"service":"service-c","status":"healthy","port":3003,"message":"..."}` |
| GET | `/greet-c` | process, then POST callback to A `/greeting-rcvd` | `{"request_id":"<id>","status":"processed","callback_sent":true}` |

## Request tracing — `X-Request-ID` (mandatory)

- On every inbound request, derive the id with `get_request_id(request.headers)`
  (returns the inbound `X-Request-ID`, or a fresh UUID if absent).
- On every **outbound** call to another service, pass it along:
  `headers={'X-Request-ID': rid}`.
- Put `request_id` on **every** log line. This is how one request is traced
  across all three services.

## Logging format (mandatory)

Use the shared logger — one JSON object per line to stdout:

```python
from lib.logger import log
log(SERVICE, event='request_received', request_id=rid, method='GET', path='/greet', status=200)
```

`timestamp` and `service` are added automatically. Always include:
`event`, `request_id`, `path`, `status`.

**Standard event names** (use these exact strings so traces line up):

| event | when |
|-------|------|
| `service_started` | on boot |
| `health_check` | `/health` hit |
| `request_received` | inbound work request received |
| `calling_downstream` | just before calling another service |
| `downstream_response` | got a response from a downstream service |
| `request_forwarded` | B forwarded to C |
| `callback_sent` | C sent its callback to A |
| `callback_received` | A received C's callback |
| `flow_completed` | A finished the whole flow |
| `request_failed` | a downstream call failed (also set `error=str(e)`) |
| `route_not_found` | unknown route (404) |

## Error responses

| Situation | HTTP status | Body |
|-----------|-------------|------|
| Unknown route | 404 | `{"status":"not_found","message":"..."}` (Django default 404 is OK too) |
| Downstream call failed (A→B, B→C) | 502 | `{"status":"error","message":"Upstream call failed","error":"..."}` |
| Callback failed (C→A) | 500 | `{"status":"error","message":"Callback failed","error":"..."}` |
| Not yet implemented (stub) | 501 | `{"status":"not_implemented","todo":"..."}` |

## How to verify your service matches the contract

```bash
# from repo root, with the venv active:
./scripts/run-local.sh
curl -s http://127.0.0.1:3001/health        # A
curl -s http://127.0.0.1:3002/health        # B
curl -s http://127.0.0.1:3003/health        # C
curl -s -H "X-Request-ID: t1" http://127.0.0.1:3001/greet-service-b   # full flow once all are done
```
