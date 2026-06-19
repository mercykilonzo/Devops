"""Service B — internal forwarder (Service A -> Service C).

Internal only: bound to 127.0.0.1, no Nginx route, blocked by UFW.

Routes:
  GET /health  health check
  GET /greet   forward to Service C /greet-c, propagating X-Request-ID

Uses the shared lib: log(), request_json(), get_request_id().
See docs/API_CONTRACT.md.
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