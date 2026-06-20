"""Minimal JSON HTTP client built on the Python standard library (urllib).

Used for service-to-service calls. The caller passes a full URL that uses a
*service-discovery name* (e.g. http://service-b.internal:3002/greet), never a
hardcoded IP. Name resolution is handled by the OS resolver (/etc/hosts).

Raises on connection failure or timeout so the caller can log a structured
`request_failed` event and return a 502.
"""

import json
import urllib.request


def request_json(url, method="GET", headers=None, body=None, timeout=5.0):
    hdrs = dict(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    hdrs.setdefault("Accept", "application/json")

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else None
        except ValueError:
            parsed = raw
        return {"status": resp.status, "body": parsed}
