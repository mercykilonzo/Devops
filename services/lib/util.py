"""Small request-handling helpers shared by all services."""

import uuid


def get_request_id(headers):
    """Return the inbound X-Request-ID, or generate one if absent.

    `headers` is the http.server message object (case-insensitive .get).
    This is the entry point for request tracing.
    """
    rid = headers.get("X-Request-ID")
    if rid and rid.strip():
        return rid.strip()
    return str(uuid.uuid4())
