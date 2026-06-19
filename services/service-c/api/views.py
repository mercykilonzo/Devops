"""Service C — INTERNAL PROCESSOR + CALLBACK to Service A.

  >>> OWNER: __________  (assign one teammate)

Internal only: bound to 127.0.0.1, no Nginx route, blocked by UFW.
Implement the TODO endpoint by following docs/API_CONTRACT.md.

Endpoints you own:
  GET /health   -> DONE (reference implementation)
  GET /greet-c  -> TODO: process, then POST a callback to Service A /greeting-rcvd

Helpers available from the shared lib (do not modify lib/):
  log(SERVICE, event=..., request_id=..., path=..., status=...)
  request_json(url, method=, headers=, body=)  -> {'status','body'}
  get_request_id(request.headers)
"""

import os
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from lib.logger import log
from lib.http_client import request_json
from lib.util import get_request_id

SERVICE = 'service-c'
PORT = int(os.environ.get('PORT', '3003'))
SERVICE_A_URL = os.environ.get('SERVICE_A_URL', 'http://service-a.internal:3001')


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
def greet_c(request):
    rid = get_request_id(request.headers)
    # TODO (Service C owner): process, then call back Service A.
    #   1. log(SERVICE, event='request_received', request_id=rid, method='GET',
    #          path='/greet-c', status=200)
    #   2. callback_body = {
    #          'request_id': rid, 'source_service': SERVICE,
    #          'message': 'Greeting processed',
    #          'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
    #      }
    #   3. request_json(f'{SERVICE_A_URL}/greeting-rcvd', method='POST',
    #                   headers={'X-Request-ID': rid}, body=callback_body)
    #   4. log(SERVICE, event='callback_sent', request_id=rid, target='service-a')
    #   5. return JsonResponse({'request_id': rid, 'status': 'processed',
    #                           'callback_sent': True})
    #   On error: log(event='request_failed', status=500) + return status=500.
    log(SERVICE, event='not_implemented', request_id=rid, method='GET', path='/greet-c', status=501)
    return JsonResponse(
        {'status': 'not_implemented', 'todo': 'Service C: process + callback to Service A'},
        status=501,
    )
