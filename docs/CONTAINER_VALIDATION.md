# Container Validation

Evidence that the containerized stack (Docker Compose) preserves the production
behavior from the VM version. Nginx is the only service that publishes a host
port, so the **public route is `http://localhost:8080/service-a/...`**.

Captured against the `feature/docker` build (`docker compose up --build -d`).

---

## 1. Start the system

```bash
docker compose up --build -d
```

```text
 Container service-b  Started
 Container service-c  Started
 Container service-a  Started
 Container nginx      Started
```

## 2. Containers are running

```bash
docker compose ps
```

Only `nginx` publishes a host port (`0.0.0.0:8080->80`); A/B/C expose their
ports to the internal network only.

```text
NAME        IMAGE               COMMAND                  SERVICE     STATUS         PORTS
nginx       nginx:1.27-alpine   "/docker-entrypoint.…"   nginx       Up            0.0.0.0:8080->80/tcp, [::]:8080->80/tcp
service-a   devops-service-a    "gunicorn service_a.…"   service-a   Up            3001/tcp
service-b   devops-service-b    "gunicorn service_b.…"   service-b   Up            3002/tcp
service-c   devops-service-c    "gunicorn service_c.…"   service-c   Up            3003/tcp
```

## 3. Public entry point works (through Nginx)

```bash
curl -i http://localhost:8080/service-a/health
curl -i http://localhost:8080/service-a/greet-service-b
```

```text
HTTP/1.1 200 OK
Server: nginx/1.27.5
Content-Type: application/json

{"service": "service-a", "status": "healthy", "port": 3001, "message": "Hello service-a listening on 3001"}

HTTP/1.1 200 OK
Server: nginx/1.27.5
Content-Type: application/json
X-Request-ID: demo-container-001

{"request_id": "demo-container-001", "status": "success", "message": "Request completed successfully"}
```

## 4. Service B and C are NOT directly exposed

```bash
curl -i --connect-timeout 3 http://localhost:3002/health
curl -i --connect-timeout 3 http://localhost:3003/health
```

```text
curl: (7) Failed to connect to localhost port 3002: Connection refused
curl: (7) Failed to connect to localhost port 3003: Connection refused
```

## 5. Internal service discovery works (Compose service names)

```bash
docker compose exec service-a curl -s -o /dev/null -w "%{http_code}\n" http://service-b:3002/health
docker compose exec service-b curl -s -o /dev/null -w "%{http_code}\n" http://service-c:3003/health
```

```text
service-a -> http://service-b:3002/health = HTTP 200
service-b -> http://service-c:3003/health = HTTP 200
```

## 6. Trace one request across all services

```bash
curl -i http://localhost:8080/service-a/greet-service-b -H "X-Request-ID: demo-container-001"
docker compose logs | grep demo-container-001
```

The same `request_id` appears in service-a, service-b, and service-c:

```text
{"service": "service-a", "event": "request_received",  "request_id": "demo-container-001", "path": "/greet-service-b", "status": 200}
{"service": "service-a", "event": "calling_downstream","request_id": "demo-container-001", "target": "service-b"}
{"service": "service-b", "event": "request_received",  "request_id": "demo-container-001", "path": "/greet", "status": 200}
{"service": "service-b", "event": "calling_downstream","request_id": "demo-container-001"}
{"service": "service-c", "event": "request_received",  "request_id": "demo-container-001", "path": "/greet-c", "status": 200}
{"service": "service-c", "event": "callback_sent",     "request_id": "demo-container-001", "target": "service-a"}
{"service": "service-a", "event": "callback_received", "request_id": "demo-container-001", "path": "/greeting-rcvd", "status": 200}
{"service": "service-b", "event": "request_forwarded", "request_id": "demo-container-001", "target": "service-c", "status": 200}
{"service": "service-a", "event": "downstream_response","request_id": "demo-container-001", "target": "service-b", "status": 200}
{"service": "service-a", "event": "flow_completed",    "request_id": "demo-container-001", "path": "/greet-service-b", "status": 200}
```

## 7. Stop Service B — clean failure, then recovery

```bash
docker compose stop service-b
curl -i http://localhost:8080/service-a/greet-service-b -H "X-Request-ID: fail-service-b-001"
docker compose logs service-a | grep fail-service-b-001
```

The client gets a clean `502`; Service A logs a `request_failed` event:

```text
HTTP/1.1 502 ...
{"service": "service-a", "event": "request_received", "request_id": "fail-service-b-001", "path": "/greet-service-b", "status": 200}
{"service": "service-a", "event": "calling_downstream","request_id": "fail-service-b-001", "target": "service-b"}
{"service": "service-a", "event": "request_failed",    "request_id": "fail-service-b-001", "path": "/greet-service-b", "status": 502, "error": "<urlopen error [Errno -2] Name or service not known>"}
```

```bash
docker compose start service-b
curl -i http://localhost:8080/service-a/greet-service-b
```

```text
HTTP/1.1 200 OK   ← system recovered
{"request_id": "...", "status": "success", "message": "Request completed successfully"}
```

---

## Shut down

```bash
docker compose down
```
