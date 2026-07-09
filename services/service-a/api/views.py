"""Service A — public entry point (reached through Nginx on port 80).

Routes:
  GET  /health           health check (shows dependency status)
  GET  /metrics          Prometheus metrics
  GET  /greet-service-b  start the A -> B -> C -> A flow
  POST /greeting-rcvd    receive the callback from Service C
  GET  /slow             controlled slow response (lab only)
  GET  /fail             controlled failure (lab only)
"""

import json
import os
import time
import uuid

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
)

from lib.logger import log
from lib.http_client import request_json
from lib.util import get_request_id

SERVICE = 'service-a'
PORT = int(os.environ.get('PORT', '3001'))
SERVICE_B_URL = os.environ.get('SERVICE_B_URL', 'http://service-b.internal:3002')

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['service', 'method', 'route', 'status_code']
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['service', 'method', 'route']
)
ERROR_COUNT = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['service', 'route']
)
SERVICE_UP = Gauge('service_up', 'Service up status', ['service'])
SERVICE_UP.labels(service=SERVICE).set(1)


@require_http_methods(['GET'])
def health(request):
    rid = get_request_id(request.headers)
    start = time.time()
    dep_status = 'ok'
    overall_status = 'healthy'
    try:
        request_json(f'{SERVICE_B_URL}/health', method='GET',
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
        'dependencies': {'service-b': dep_status},
    })


@require_http_methods(['GET'])
def metrics(request):
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)


@require_http_methods(['GET'])
def greet_service_b(request):
    rid = get_request_id(request.headers)
    start = time.time()
    trace_id = str(uuid.uuid4())
    log(SERVICE, event='request_received', request_id=rid, trace_id=trace_id,
        method='GET', path='/greet-service-b', status=200)
    log(SERVICE, event='calling_downstream', request_id=rid, trace_id=trace_id,
        target='service-b', path='/greet')
    try:
        resp = request_json(f'{SERVICE_B_URL}/greet', method='GET',
                            headers={'X-Request-ID': rid, 'X-Trace-ID': trace_id})
    except Exception as e:
        duration = time.time() - start
        REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/greet-service-b', status_code=502).inc()
        ERROR_COUNT.labels(service=SERVICE, route='/greet-service-b').inc()
        REQUEST_DURATION.labels(service=SERVICE, method='GET', route='/greet-service-b').observe(duration)
        log(SERVICE, event='request_failed', request_id=rid, trace_id=trace_id,
            method='GET', path='/greet-service-b', status=502, error=str(e))
        return JsonResponse(
            {'status': 'error', 'message': 'Upstream call failed', 'error': str(e)},
            status=502,
        )
    duration = time.time() - start
    REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/greet-service-b', status_code=200).inc()
    REQUEST_DURATION.labels(service=SERVICE, method='GET', route='/greet-service-b').observe(duration)
    log(SERVICE, event='flow_completed', request_id=rid, trace_id=trace_id,
        method='GET', path='/greet-service-b', status=200, duration_ms=round(duration * 1000))
    return JsonResponse({
        'request_id': rid,
        'trace_id': trace_id,
        'status': 'success',
        'message': 'Request completed successfully',
    })


@csrf_exempt
@require_http_methods(['POST'])
def greeting_rcvd(request):
    rid = get_request_id(request.headers)
    try:
        body = json.loads(request.body) if request.body else {}
    except ValueError:
        body = {}
    rid = body.get('request_id') or rid
    log(SERVICE, event='callback_received', request_id=rid,
        source_service=body.get('source_service', 'service-c'),
        method='POST', path='/greeting-rcvd', status=200)
    return JsonResponse({'status': 'received'})


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
