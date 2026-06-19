"""Service A — public entry point (reached through Nginx on port 80).

Routes:
  GET  /health           health check
  GET  /greet-service-b  start the A -> B -> C -> A flow; call Service B /greet
  POST /greeting-rcvd    receive the callback from Service C

Uses the shared lib: log() (structured JSON), request_json() (HTTP client),
get_request_id() (X-Request-ID tracing). See docs/API_CONTRACT.md.
"""

import json
import os

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from lib.logger import log
from lib.http_client import request_json
from lib.util import get_request_id

SERVICE = 'service-a'
PORT = int(os.environ.get('PORT', '3001'))
SERVICE_B_URL = os.environ.get('SERVICE_B_URL', 'http://service-b.internal:3002')


@require_http_methods(['GET'])
def health(request):
    """Health check — returns 200 with service name, port, and status."""
    rid = get_request_id(request.headers)
    log(SERVICE, event='health_check', request_id=rid, method='GET', path='/health', status=200)
    return JsonResponse({
        'service': SERVICE,
        'status': 'healthy',
        'port': PORT,
        'message': f'Hello {SERVICE} listening on {PORT}',
    })



@require_http_methods(['GET'])
def greet_service_b(request):
    rid = get_request_id(request.headers)
    log(SERVICE, event='request_received', request_id=rid, method='GET',
        path='/greet-service-b', status=200)

    log(SERVICE, event='calling_downstream', request_id=rid, target='service-b', path='/greet')
    try:
        resp = request_json(f'{SERVICE_B_URL}/greet', method='GET',
                            headers={'X-Request-ID': rid})
    except Exception as e:
        log(SERVICE, event='request_failed', request_id=rid, method='GET',
            path='/greet-service-b', status=502, error=str(e))
        return JsonResponse(
            {'status': 'error', 'message': 'Upstream call failed', 'error': str(e)},
            status=502,
        )

    log(SERVICE, event='downstream_response', request_id=rid, target='service-b',
        status=resp['status'])
    log(SERVICE, event='flow_completed', request_id=rid, method='GET',
        path='/greet-service-b', status=200)
    return JsonResponse({
        'request_id': rid,
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
