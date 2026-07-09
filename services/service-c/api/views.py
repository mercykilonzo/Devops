"""Service C — internal processor + callback to Service A.

Routes:
  GET /health   health check
  GET /metrics  Prometheus metrics
  GET /greet-c  process request, POST callback to Service A
  GET /slow     controlled slow response (lab only)
  GET /fail     controlled failure (lab only)
"""

import os
import time
import uuid
from datetime import datetime, timezone

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
)

from lib.logger import log
from lib.http_client import request_json
from lib.util import get_request_id

SERVICE = 'service-c'
PORT = int(os.environ.get('PORT', '3003'))
SERVICE_A_URL = os.environ.get('SERVICE_A_URL', 'http://service-a.internal:3001')

REQUEST_COUNT = Counter(
    'http_requests_total_c',
    'Total HTTP requests',
    ['service', 'method', 'route', 'status_code']
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds_c',
    'HTTP request duration in seconds',
    ['service', 'method', 'route']
)
ERROR_COUNT = Counter(
    'http_errors_total_c',
    'Total HTTP errors',
    ['service', 'route']
)
SERVICE_UP = Gauge('service_up_c', 'Service up status', ['service'])
SERVICE_UP.labels(service=SERVICE).set(1)


@require_http_methods(['GET'])
def health(request):
    rid = get_request_id(request.headers)
    start = time.time()
    duration = time.time() - start
    REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/health', status_code=200).inc()
    REQUEST_DURATION.labels(service=SERVICE, method='GET', route='/health').observe(duration)
    log(SERVICE, event='health_check', request_id=rid, method='GET', path='/health', status=200)
    return JsonResponse({
        'service': SERVICE,
        'status': 'healthy',
        'port': PORT,
        'message': f'Hello {SERVICE} listening on {PORT}',
        'dependencies': {},
    })


@require_http_methods(['GET'])
def metrics(request):
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)


@require_http_methods(['GET'])
def greet_c(request):
    rid = get_request_id(request.headers)
    trace_id = request.headers.get('X-Trace-ID', str(uuid.uuid4()))
    start = time.time()
    try:
        log(SERVICE, event='request_received', request_id=rid, trace_id=trace_id,
            method='GET', path='/greet-c', status=200)
        callback_body = {
            'request_id': rid,
            'source_service': SERVICE,
            'message': 'Greeting processed',
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        }
        request_json(
            f'{SERVICE_A_URL}/greeting-rcvd',
            method='POST',
            headers={'X-Request-ID': rid, 'X-Trace-ID': trace_id},
            body=callback_body,
        )
        duration = time.time() - start
        REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/greet-c', status_code=200).inc()
        REQUEST_DURATION.labels(service=SERVICE, method='GET', route='/greet-c').observe(duration)
        log(SERVICE, event='callback_sent', request_id=rid, trace_id=trace_id,
            target='service-a', duration_ms=round(duration * 1000))
        return JsonResponse({'request_id': rid, 'status': 'processed', 'callback_sent': True})
    except Exception as e:
        duration = time.time() - start
        REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/greet-c', status_code=500).inc()
        ERROR_COUNT.labels(service=SERVICE, route='/greet-c').inc()
        REQUEST_DURATION.labels(service=SERVICE, method='GET', route='/greet-c').observe(duration)
        log(SERVICE, event='request_failed', request_id=rid, trace_id=trace_id,
            method='GET', path='/greet-c', status=500, error=str(e))
        return JsonResponse(
            {'status': 'error', 'message': 'Callback failed', 'error': str(e)},
            status=500,
        )


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
