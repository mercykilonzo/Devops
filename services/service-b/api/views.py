"""Service B — INTERNAL FORWARDER (Service A -> Service C).

  >>> OWNER: __________  (assign one teammate)

Internal only: bound to 127.0.0.1, no Nginx route, blocked by UFW.
Implement the TODO endpoint by following docs/API_CONTRACT.md.

Endpoints you own:
  GET /health  -> DONE (reference implementation)
  GET /greet   -> DONE: forwards to Service C /greet-c, propagating X-Request-ID

Helpers available from the shared lib (do not modify lib/):
  log(SERVICE, event=..., request_id=..., path=..., status=...)
  request_json(url, method=, headers=, body=)  -> {'status','body'}
  get_request_id(request.headers)
"""

import os

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from lib.logger import log
from lib.http_client import request_json
from lib.util import get_request_id

SERVICE = 'service-b'
PORT = int(os.environ.get('PORT', '3002'))
SERVICE_C_URL = os.environ.get('SERVICE_C_URL', 'http://service-c.internal:3003')


@require_http_methods(['GET'])
def health(request):
    """DONE — reference implementation."""
    rid = get_request_id(request.headers)
    log(SERVICE, event='health_check', request_id=rid, method='GET', path='/health', status=200)
    return JsonResponse({
        'service': SERVICE,
        'status': 'healthy',
        'port': PORT,
        'message': f'Hello {SERVICE} listening on {PORT}',
    })


@require_http_methods(['GET'])
def greet(request):
    rid = get_request_id(request.headers)
    log(SERVICE, event='request_received', request_id=rid, method='GET', path='/greet', status=200)

    log(SERVICE, event='calling_downstream', request_id=rid, path='/greet', status=200)
    try:
        resp = request_json(f'{SERVICE_C_URL}/greet-c', method='GET', headers={'X-Request-ID': rid})
    except Exception as e:
        log(SERVICE, event='request_failed', request_id=rid, path='/greet', status=502, error=str(e))
        return JsonResponse(
            {'status': 'error', 'message': 'Upstream call failed', 'error': str(e)},
            status=502,
        )

    log(SERVICE, event='downstream_response', request_id=rid, target='service-c', status=resp['status'])
    log(SERVICE, event='request_forwarded', request_id=rid, target='service-c', status=resp['status'])
    return JsonResponse({'request_id': rid, 'status': 'forwarded', 'target': 'service-c'})