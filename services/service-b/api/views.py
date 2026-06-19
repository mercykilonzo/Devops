"""Service B — INTERNAL FORWARDER (Service A -> Service C).

  >>> OWNER: __________  (assign one teammate)

Internal only: bound to 127.0.0.1, no Nginx route, blocked by UFW.
Implement the TODO endpoint by following docs/API_CONTRACT.md.

Endpoints you own:
  GET /health  -> DONE (reference implementation)
  GET /greet   -> TODO: forward to Service C /greet-c, propagating X-Request-ID

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
    # TODO (Service B owner): forward the request to Service C.
    #   1. log(SERVICE, event='request_received', request_id=rid, method='GET',
    #          path='/greet', status=200)
    #   2. resp = request_json(f'{SERVICE_C_URL}/greet-c', method='GET',
    #                          headers={'X-Request-ID': rid})
    #   3. log(SERVICE, event='request_forwarded', request_id=rid,
    #          target='service-c', status=resp['status'])
    #   4. return JsonResponse({'request_id': rid, 'status': 'forwarded',
    #                           'target': 'service-c'})
    #   On error: log(event='request_failed', status=502) + return status=502.
    log(SERVICE, event='not_implemented', request_id=rid, method='GET', path='/greet', status=501)
    return JsonResponse(
        {'status': 'not_implemented', 'todo': 'Service B: forward to Service C'},
        status=501,
    )
