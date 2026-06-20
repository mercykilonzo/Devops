"""Structured JSON logger.

Every service writes one JSON object per line to stdout. systemd captures
stdout into the journal, so logs are viewable with:

    journalctl -t service-a -o cat

`timestamp` (ISO-8601, UTC) and `service` are always stamped; callers pass the
event-specific fields as keyword arguments (event, request_id, path, status...).

stdout is flushed on every line so logs appear immediately under journald
(Python block-buffers stdout when it is not a TTY).
"""

import json
import sys
from datetime import datetime, timezone


def log(service, **fields):
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "service": service,
    }
    entry.update(fields)
    sys.stdout.write(json.dumps(entry) + "\n")
    sys.stdout.flush()
