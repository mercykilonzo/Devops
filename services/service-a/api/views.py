"""Service A — PUBLIC ENTRY POINT (reached through Nginx on port 80).

  >>> OWNER: __________  (assign one teammate)

Implement the TODO endpoints below by following docs/API_CONTRACT.md.
`/health` is already done — copy its logging style for the others.

Endpoints you own (see contract for exact request/response shapes):
  GET  /health           -> DONE (reference implementation)
  GET  /greet-service-b  -> TODO: start the flow, call Service B /greet
  POST /greeting-rcvd    -> TODO: receive the callback from Service C

Helpers available from the shared lib (do not modify lib/):
  log(SERVICE, event=..., request_id=..., path=..., status=...)  -> JSON log line
  request_json(url, method=, headers=, body=)                    -> {'status','body'}
  get_request_id(request.headers)                                -> trace id (X-Request-ID or new)
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
    """DONE — reference implementation. Returns 200 + service info."""
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
