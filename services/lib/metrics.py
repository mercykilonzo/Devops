"""Shared Prometheus metrics registry.

All three services import from here so metric names and label sets
are consistent across the platform.

Usage in views.py:
    from lib.metrics import REQUEST_COUNT, REQUEST_LATENCY, ERROR_COUNT, SERVICE_UP
    import time

    start = time.time()
    ...
    duration = time.time() - start
    REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/health', status_code='200').inc()
    REQUEST_LATENCY.labels(service=SERVICE, route='/health').observe(duration)

Multi-worker note:
    gunicorn runs several worker processes. Without multiprocess mode each worker
    keeps its own in-memory counters and Prometheus scrapes only one of them, so
    totals undercount and jump between scrapes. When PROMETHEUS_MULTIPROC_DIR is
    set (see the Dockerfile / gunicorn_conf.py), prometheus_client writes metrics
    to shared files and `render_metrics()` aggregates every worker on scrape.
"""

import os

from prometheus_client import (
    Counter, Histogram, Gauge, CollectorRegistry, REGISTRY,
    CONTENT_TYPE_LATEST, generate_latest, multiprocess,
)

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['service', 'method', 'route', 'status_code'],
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['service', 'route'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

ERROR_COUNT = Counter(
    'http_errors_total',
    'Total HTTP errors (4xx/5xx)',
    ['service', 'route'],
)

SERVICE_UP = Gauge(
    'service_up',
    'Whether this service is up (1) or down (0)',
    ['service'],
    multiprocess_mode='liveall',  # required so the gauge works under multiprocess
)


def render_metrics():
    """Return (body, content_type) for the /metrics endpoint.

    Under gunicorn multiprocess mode, aggregate every worker's metrics into a
    fresh registry so scrapes read a stable, correct total. Falls back to the
    default registry for single-process runs (e.g. `manage.py runserver`).
    """
    if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    else:
        registry = REGISTRY
    return generate_latest(registry), CONTENT_TYPE_LATEST
