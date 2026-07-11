# Benchmark Report

## Test Tool

`ab` (Apache Benchmark) — included in the `apache2-utils` package.

```bash
sudo apt install apache2-utils
```

## Test Command

```bash
# Run all three scenarios in sequence
./scripts/load-test.sh all

# Or individually:
./scripts/load-test.sh normal
./scripts/load-test.sh stress
./scripts/load-test.sh failure
```

## Results

### Scenario 1: Normal Traffic

| Metric           | Value          |
|------------------|----------------|
| Requests         | 500            |
| Concurrency      | 10             |
| Target endpoint  | /greet-service-b |
| Avg latency      | ~40ms          |
| p95 latency      | ~120ms         |
| Error rate       | 0%             |
| Alert triggered  | None           |

**Metrics observed:** Request rate in Grafana shows ~25 req/s. Error rate panel stays at 0.
p95 latency panel stays below 0.15s.

---

### Scenario 2: Stress Traffic

| Metric           | Value          |
|------------------|----------------|
| Requests         | 2000           |
| Concurrency      | 50             |
| Target endpoint  | /greet-service-b |
| Avg latency      | ~180ms         |
| p95 latency      | ~650ms         |
| Error rate       | ~2%            |
| Alert triggered  | HighLatency (p95 > 500ms after ~2min sustained) |

**Metrics observed:** p95 latency panel crosses 0.5s threshold. Grafana shows request
rate spike to ~100 req/s. Some requests fail with 502 (gunicorn worker contention).

**Traces observed:** Jaeger shows longer spans for `/greet-service-b`. The slow portion
is inside the service-b → service-c call, confirming the bottleneck is downstream.

---

### Scenario 3: Failure Traffic

| Metric           | Value          |
|------------------|----------------|
| Requests         | 300            |
| Concurrency      | 10             |
| Target endpoint  | /fail          |
| Avg latency      | <5ms           |
| p95 latency      | <5ms           |
| Error rate       | 100%           |
| Alert triggered  | HighErrorRate  |

**Metrics observed:** `http_errors_total` counter jumps immediately.
`rate(http_errors_total[2m])` crosses 0.1/s within 30 seconds.
Prometheus fires the HighErrorRate alert after the 2-minute `for` window.

**Logs observed:**
```json
{"timestamp":"...","service":"service-a","event":"fail_endpoint_called",
 "request_id":"...","status":500,"error":"controlled failure","duration_ms":0}
```

---

## Failure Simulation

### Failure C: High Error Rate via /fail

**Steps:**
```bash
# In one terminal — hammer the fail endpoint
./scripts/load-test.sh failure

# In another terminal — watch error rate in Prometheus
watch -n5 'curl -s "http://localhost:9090/api/v1/query?query=rate(http_errors_total[2m])" | python3 -m json.tool'

# Check alert state
curl -s http://localhost:9090/api/v1/rules | python3 -m json.tool | grep -A3 HighErrorRate
```

**MELT evidence collected:**

| Signal  | Evidence |
|---------|----------|
| Metrics | `rate(http_errors_total[2m]) > 0.1` — Prometheus alert fires |
| Events  | Log event `fail_endpoint_called` with `status:500` |
| Logs    | `docker compose logs service-a` shows structured error entries |
| Traces  | Jaeger shows `/fail` spans marked as errors |

---

## Lessons Learned

1. **Instrumentation gap = invisible failure.** Before adding `/metrics`, the only way
   to detect errors was to read logs manually. Prometheus makes the same fact queryable.

2. **p95 matters more than average.** Under stress traffic, average latency looked
   acceptable (~180ms) but p95 hit 650ms — affecting 1 in 20 users significantly.

3. **Logs and traces are complementary.** Prometheus showed *that* errors occurred.
   Structured logs showed *what* the error was. Jaeger showed *which service* was
   responsible in the call chain.

4. **Named volumes protect your data.** Restarting Prometheus without a named volume
   loses all historical metrics. `prometheus-data` named volume ensures persistence.

5. **Controlled failures are required for trust.** You cannot verify that alerting works
   without safely causing the condition the alert is supposed to detect.
