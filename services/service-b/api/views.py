"""Service B — internal forwarder (Service A -> Service C).

Routes:
  GET /health   health check
  GET /metrics  Prometheus metrics
  GET /greet    forward to Service C /greet-c, propagating X-Request-ID
  GET /slow     controlled slow endpoint (LAB ONLY)
  GET /fail     controlled failure endpoint (LAB ONLY)
"""

import os
import time

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from lib.logger import log
from lib.http_client import request_json
from lib.util import get_request_id
from lib.metrics import REQUEST_COUNT, REQUEST_LATENCY, ERROR_COUNT, SERVICE_UP, render_metrics

SERVICE = 'service-b'
PORT = int(os.environ.get('PORT', '3002'))
SERVICE_C_URL = os.environ.get('SERVICE_C_URL', 'http://service-c:3003')

SERVICE_UP.labels(service=SERVICE).set(1)


@require_http_methods(['GET'])
def health(request):
    rid = get_request_id(request.headers)
    start = time.time()
    dep_status = {}
    try:
        r = request_json(f'{SERVICE_C_URL}/health', method='GET',
                         headers={'X-Request-ID': rid})
        dep_status['service-c'] = 'ok' if r['status'] == 200 else 'degraded'
    except Exception:
        dep_status['service-c'] = 'unreachable'

    overall = 'ok' if all(v == 'ok' for v in dep_status.values()) else 'degraded'
    duration = time.time() - start
    log(SERVICE, event='health_check', request_id=rid, method='GET',
        path='/health', status=200, duration_ms=round(duration * 1000))
    REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/health', status_code='200').inc()
    REQUEST_LATENCY.labels(service=SERVICE, route='/health').observe(duration)
    return JsonResponse({
        'service': SERVICE,
        'status': overall,
        'port': PORT,
        'dependencies': dep_status,
    })


@require_http_methods(['GET'])
def metrics(request):
    body, content_type = render_metrics()
    return HttpResponse(body, content_type=content_type)


@require_http_methods(['GET'])
def greet(request):
    rid = get_request_id(request.headers)
    start = time.time()
    log(SERVICE, event='request_received', request_id=rid, method='GET',
        path='/greet', trace_id=rid)
    try:
        resp = request_json(f'{SERVICE_C_URL}/greet-c', method='GET',
                            headers={'X-Request-ID': rid})
    except Exception as e:
        duration = time.time() - start
        log(SERVICE, event='request_failed', request_id=rid, path='/greet',
            status=502, error=str(e), duration_ms=round(duration * 1000))
        REQUEST_COUNT.labels(service=SERVICE, method='GET',
                             route='/greet', status_code='502').inc()
        ERROR_COUNT.labels(service=SERVICE, route='/greet').inc()
        REQUEST_LATENCY.labels(service=SERVICE, route='/greet').observe(duration)
        return JsonResponse(
            {'status': 'error', 'message': 'Upstream call failed', 'error': str(e)},
            status=502,
        )

    duration = time.time() - start
    log(SERVICE, event='request_forwarded', request_id=rid, target='service-c',
        status=resp['status'], duration_ms=round(duration * 1000), trace_id=rid)
    REQUEST_COUNT.labels(service=SERVICE, method='GET',
                         route='/greet', status_code='200').inc()
    REQUEST_LATENCY.labels(service=SERVICE, route='/greet').observe(duration)
    return JsonResponse({'request_id': rid, 'status': 'forwarded', 'target': 'service-c'})


@require_http_methods(['GET'])
def slow(request):
    rid = get_request_id(request.headers)
    start = time.time()
    log(SERVICE, event='slow_endpoint_called', request_id=rid,
        method='GET', path='/slow')
    time.sleep(2)
    duration = time.time() - start
    log(SERVICE, event='slow_endpoint_done', request_id=rid,
        method='GET', path='/slow', status=200,
        duration_ms=round(duration * 1000))
    REQUEST_COUNT.labels(service=SERVICE, method='GET',
                         route='/slow', status_code='200').inc()
    REQUEST_LATENCY.labels(service=SERVICE, route='/slow').observe(duration)
    return JsonResponse({'status': 'ok', 'note': 'LAB-ONLY slow endpoint',
                         'duration_ms': round(duration * 1000)})


@require_http_methods(['GET'])
def fail(request):
    rid = get_request_id(request.headers)
    start = time.time()
    duration = time.time() - start
    log(SERVICE, event='fail_endpoint_called', request_id=rid,
        method='GET', path='/fail', status=500, error='controlled failure',
        duration_ms=round(duration * 1000))
    REQUEST_COUNT.labels(service=SERVICE, method='GET',
                         route='/fail', status_code='500').inc()
    ERROR_COUNT.labels(service=SERVICE, route='/fail').inc()
    REQUEST_LATENCY.labels(service=SERVICE, route='/fail').observe(duration)
    return JsonResponse({'status': 'error', 'note': 'LAB-ONLY controlled failure'}, status=500)
