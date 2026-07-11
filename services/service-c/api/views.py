"""Service C — internal processor + callback to Service A.

Routes:
  GET /health   health check
  GET /metrics  Prometheus metrics
  GET /greet-c  process request, POST callback to Service A /greeting-rcvd
  GET /slow     controlled slow endpoint (LAB ONLY)
  GET /fail     controlled failure endpoint (LAB ONLY)
"""

import os
import time
from datetime import datetime, timezone

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from lib.logger import log
from lib.http_client import request_json
from lib.util import get_request_id
from lib.metrics import REQUEST_COUNT, REQUEST_LATENCY, ERROR_COUNT, SERVICE_UP, render_metrics

SERVICE = 'service-c'
PORT = int(os.environ.get('PORT', '3003'))
SERVICE_A_URL = os.environ.get('SERVICE_A_URL', 'http://service-a:3001')

SERVICE_UP.labels(service=SERVICE).set(1)


@require_http_methods(['GET'])
def health(request):
    rid = get_request_id(request.headers)
    start = time.time()
    duration = time.time() - start
    log(SERVICE, event='health_check', request_id=rid, method='GET',
        path='/health', status=200, duration_ms=round(duration * 1000))
    REQUEST_COUNT.labels(service=SERVICE, method='GET', route='/health', status_code='200').inc()
    REQUEST_LATENCY.labels(service=SERVICE, route='/health').observe(duration)
    return JsonResponse({
        'service': SERVICE,
        'status': 'ok',
        'port': PORT,
        'dependencies': {},
    })


@require_http_methods(['GET'])
def metrics(request):
    body, content_type = render_metrics()
    return HttpResponse(body, content_type=content_type)


@require_http_methods(['GET'])
def greet_c(request):
    rid = get_request_id(request.headers)
    start = time.time()
    try:
        log(SERVICE, event='request_received', request_id=rid, method='GET',
            path='/greet-c', trace_id=rid)

        callback_body = {
            'request_id': rid,
            'source_service': SERVICE,
            'message': 'Greeting processed',
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        }

        request_json(
            f'{SERVICE_A_URL}/greeting-rcvd',
            method='POST',
            headers={'X-Request-ID': rid},
            body=callback_body,
        )

        duration = time.time() - start
        log(SERVICE, event='callback_sent', request_id=rid, target='service-a',
            duration_ms=round(duration * 1000), trace_id=rid)
        REQUEST_COUNT.labels(service=SERVICE, method='GET',
                             route='/greet-c', status_code='200').inc()
        REQUEST_LATENCY.labels(service=SERVICE, route='/greet-c').observe(duration)
        return JsonResponse({
            'request_id': rid,
            'status': 'processed',
            'callback_sent': True,
        })

    except Exception as e:
        duration = time.time() - start
        log(SERVICE, event='request_failed', request_id=rid, method='GET',
            path='/greet-c', status=500, error=str(e),
            duration_ms=round(duration * 1000))
        REQUEST_COUNT.labels(service=SERVICE, method='GET',
                             route='/greet-c', status_code='500').inc()
        ERROR_COUNT.labels(service=SERVICE, route='/greet-c').inc()
        REQUEST_LATENCY.labels(service=SERVICE, route='/greet-c').observe(duration)
        return JsonResponse(
            {'status': 'error', 'message': 'Callback failed', 'error': str(e)},
            status=500,
        )


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
