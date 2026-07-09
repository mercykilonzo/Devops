"""Service B — internal forwarder (Service A -> Service C).

Routes:
  GET /health   health check (shows dependency status)
  GET /metrics  Prometheus metrics
  GET /greet    forward to Service C /greet-c
  GET /slow     controlled slow response (lab only)
  GET /fail     controlled failure (lab only)
"""

import os
import time
import uuid

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
)

from lib.logger import log
from lib.http_client import request_json
from lib.util import get_request_id

SERVICE = 'service-b'
PORT = int(os.environ.get('PORT', '3002'))
SERVICE_C_URL = os.environ.get('SERVICE_C_URL', 'http://service-c.internal:3003')

REQUEST_COUNT = Counter(
    'http_requests_total_b',
    'Total HTTP requests',
    ['service', 'method', 'route', 'status_code']
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds_b',
    'HTTP request duration in seconds',
    ['service', 'method', 'route']
)
ERROR_COUNT = Counter(
    'http_errors_total_b',
    'Total HTTP errors',
    ['service', 'route']
)
SERVICE_UP = Gauge('service_up_b', 'Service up status', ['service'])
SERVICE_UP.labels(service=SERVICE).set(1)


@require_http_methods(['GET'])
def health(request):
    rid = get_request_id(request.headers)
    start = time.time()
    dep_status = 'ok'
    overall_status = 'healthy'
    try:
        request_json(f'{SERVICE_C_URL}/health', method='GET',
                     headers={'X-Request-ID': rid})
    except Exception:
        dep_status = 'unreachable'
        overall_status = 'degraded'
    duration = time.time() - start
    REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/health', status_code=200).inc()
    REQUEST_DURATION.labels(service=SERVICE, method='GET', route='/health').observe(duration)
    log(SERVICE, event='health_check', request_id=rid, method='GET', path='/health', status=200)
    return JsonResponse({
        'service': SERVICE,
        'status': overall_status,
        'port': PORT,
        'message': f'Hello {SERVICE} listening on {PORT}',
        'dependencies': {'service-c': dep_status},
    })


@require_http_methods(['GET'])
def metrics(request):
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)


@require_http_methods(['GET'])
def greet(request):
    rid = get_request_id(request.headers)
    trace_id = request.headers.get('X-Trace-ID', str(uuid.uuid4()))
    start = time.time()
    log(SERVICE, event='request_received', request_id=rid, trace_id=trace_id,
        method='GET', path='/greet', status=200)
    log(SERVICE, event='calling_downstream', request_id=rid, trace_id=trace_id,
        path='/greet', status=200)
    try:
        resp = request_json(f'{SERVICE_C_URL}/greet-c', method='GET',
                            headers={'X-Request-ID': rid, 'X-Trace-ID': trace_id})
    except Exception as e:
        duration = time.time() - start
        REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/greet', status_code=502).inc()
        ERROR_COUNT.labels(service=SERVICE, route='/greet').inc()
        REQUEST_DURATION.labels(service=SERVICE, method='GET', route='/greet').observe(duration)
        log(SERVICE, event='request_failed', request_id=rid, trace_id=trace_id,
            path='/greet', status=502, error=str(e))
        return JsonResponse(
            {'status': 'error', 'message': 'Upstream call failed', 'error': str(e)},
            status=502,
        )
    duration = time.time() - start
    REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/greet', status_code=200).inc()
    REQUEST_DURATION.labels(service=SERVICE, method='GET', route='/greet').observe(duration)
    log(SERVICE, event='request_forwarded', request_id=rid, trace_id=trace_id,
        target='service-c', status=resp['status'], duration_ms=round(duration * 1000))
    return JsonResponse({'request_id': rid, 'status': 'forwarded', 'target': 'service-c'})


@require_http_methods(['GET'])
def slow(request):
    rid = get_request_id(request.headers)
    start = time.time()
    delay = float(request.GET.get('delay', '2'))
    log(SERVICE, event='slow_request_started', request_id=rid, path='/slow', delay=delay)
    time.sleep(delay)
    duration = time.time() - start
    REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/slow', status_code=200).inc()
    REQUEST_DURATION.labels(service=SERVICE, method='GET', route='/slow').observe(duration)
    log(SERVICE, event='slow_request_completed', request_id=rid, path='/slow',
        duration_ms=round(duration * 1000), status=200)
    return JsonResponse({
        'service': SERVICE, 'status': 'slow_response',
        'delay_seconds': delay, 'note': 'LAB ONLY - controlled slow endpoint',
    })


@require_http_methods(['GET'])
def fail(request):
    rid = get_request_id(request.headers)
    REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/fail', status_code=500).inc()
    ERROR_COUNT.labels(service=SERVICE, route='/fail').inc()
    log(SERVICE, event='controlled_failure', request_id=rid, path='/fail', status=500,
        error='Controlled failure triggered for observability testing')
    return JsonResponse({
        'status': 'error', 'message': 'Controlled failure triggered',
        'note': 'LAB ONLY - controlled failure endpoint',
    }, status=500)
