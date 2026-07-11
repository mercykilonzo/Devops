"""Service A — public entry point (reached through Nginx on port 80).

Routes:
  GET  /health           health check with dependency status
  GET  /metrics          Prometheus metrics
  GET  /greet-service-b  start the A -> B -> C -> A flow
  POST /greeting-rcvd    receive the callback from Service C
  GET  /slow             controlled slow endpoint (artificial 2s delay)
  GET  /fail             controlled failure endpoint (returns 500)
"""

import json
import os
import time

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from lib.logger import log
from lib.http_client import request_json
from lib.util import get_request_id
from lib.metrics import REQUEST_COUNT, REQUEST_LATENCY, ERROR_COUNT, SERVICE_UP, render_metrics

SERVICE = 'service-a'
PORT = int(os.environ.get('PORT', '3001'))
SERVICE_B_URL = os.environ.get('SERVICE_B_URL', 'http://service-b:3002')

# Mark this service as up at import time
SERVICE_UP.labels(service=SERVICE).set(1)


# ── /health ──────────────────────────────────────────────────────────────────

@require_http_methods(['GET'])
def health(request):
    rid = get_request_id(request.headers)
    start = time.time()

    # Check dependency health
    dep_status = {}
    try:
        r = request_json(f'{SERVICE_B_URL}/health', method='GET',
                         headers={'X-Request-ID': rid})
        dep_status['service-b'] = 'ok' if r['status'] == 200 else 'degraded'
    except Exception:
        dep_status['service-b'] = 'unreachable'

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


# ── /metrics ─────────────────────────────────────────────────────────────────

@require_http_methods(['GET'])
def metrics(request):
    body, content_type = render_metrics()
    return HttpResponse(body, content_type=content_type)


# ── /greet-service-b ─────────────────────────────────────────────────────────

@require_http_methods(['GET'])
def greet_service_b(request):
    rid = get_request_id(request.headers)
    start = time.time()
    log(SERVICE, event='request_received', request_id=rid, method='GET',
        path='/greet-service-b', status=200)

    try:
        resp = request_json(f'{SERVICE_B_URL}/greet', method='GET',
                            headers={'X-Request-ID': rid})
    except Exception as e:
        duration = time.time() - start
        log(SERVICE, event='request_failed', request_id=rid, method='GET',
            path='/greet-service-b', status=502, error=str(e),
            duration_ms=round(duration * 1000))
        REQUEST_COUNT.labels(service=SERVICE, method='GET',
                             route='/greet-service-b', status_code='502').inc()
        ERROR_COUNT.labels(service=SERVICE, route='/greet-service-b').inc()
        REQUEST_LATENCY.labels(service=SERVICE, route='/greet-service-b').observe(duration)
        return JsonResponse(
            {'status': 'error', 'message': 'Upstream call failed', 'error': str(e)},
            status=502,
        )

    duration = time.time() - start
    log(SERVICE, event='flow_completed', request_id=rid, method='GET',
        path='/greet-service-b', status=200, duration_ms=round(duration * 1000),
        trace_id=rid)
    REQUEST_COUNT.labels(service=SERVICE, method='GET',
                         route='/greet-service-b', status_code='200').inc()
    REQUEST_LATENCY.labels(service=SERVICE, route='/greet-service-b').observe(duration)
    return JsonResponse({
        'request_id': rid,
        'status': 'success',
        'message': 'Request completed successfully',
    })


# ── /greeting-rcvd ───────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def greeting_rcvd(request):
    rid = get_request_id(request.headers)
    start = time.time()
    try:
        body = json.loads(request.body) if request.body else {}
    except ValueError:
        body = {}
    rid = body.get('request_id') or rid
    duration = time.time() - start
    log(SERVICE, event='callback_received', request_id=rid,
        source_service=body.get('source_service', 'service-c'),
        method='POST', path='/greeting-rcvd', status=200,
        duration_ms=round(duration * 1000))
    REQUEST_COUNT.labels(service=SERVICE, method='POST',
                         route='/greeting-rcvd', status_code='200').inc()
    REQUEST_LATENCY.labels(service=SERVICE, route='/greeting-rcvd').observe(duration)
    return JsonResponse({'status': 'received'})


# ── /slow  (controlled failure — LAB ONLY) ───────────────────────────────────

@require_http_methods(['GET'])
def slow(request):
    """Artificial 2-second delay to trigger the HighLatency alert."""
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
    return JsonResponse({'status': 'ok', 'note': 'LAB-ONLY slow endpoint', 'duration_ms': round(duration * 1000)})


# ── /fail  (controlled failure — LAB ONLY) ───────────────────────────────────

@require_http_methods(['GET'])
def fail(request):
    """Always returns 500 to trigger the HighErrorRate alert."""
    rid = get_request_id(request.headers)
    start = time.time()
    duration = time.time() - start
    log(SERVICE, event='fail_endpoint_called', request_id=rid,
        method='GET', path='/fail', status=500,
        duration_ms=round(duration * 1000),
        error='controlled failure')
    REQUEST_COUNT.labels(service=SERVICE, method='GET',
                         route='/fail', status_code='500').inc()
    ERROR_COUNT.labels(service=SERVICE, route='/fail').inc()
    REQUEST_LATENCY.labels(service=SERVICE, route='/fail').observe(duration)
    return JsonResponse({'status': 'error', 'note': 'LAB-ONLY controlled failure'}, status=500)
