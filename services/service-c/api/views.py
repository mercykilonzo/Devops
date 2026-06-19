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

    try:
        log(
            SERVICE,
            event='request_received',
            request_id=rid,
            method='GET',
            path='/greet-c',
            status=200,
        )

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

        log(
            SERVICE,
            event='callback_sent',
            request_id=rid,
            target='service-a',
        )

        return JsonResponse({
            'request_id': rid,
            'status': 'processed',
            'callback_sent': True,
        })

    except Exception as e:
        log(
            SERVICE,
            event='request_failed',
            request_id=rid,
            method='GET',
            path='/greet-c',
            status=500,
            error=str(e),
        )

        return JsonResponse(
            {
                'status': 'error',
                'message': 'Callback failed',
                'error': str(e),
            },
            status=500,
        )