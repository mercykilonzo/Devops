"""Shared gunicorn config — enables correct Prometheus metrics under multiple
workers.

prometheus_client multiprocess mode writes per-process metric files into
PROMETHEUS_MULTIPROC_DIR. We clear that directory once before workers fork
(so a restarted container doesn't read stale files) and mark each worker's
files dead when it exits, so `render_metrics()` aggregates only live data.

Referenced via `gunicorn -c /app/lib/gunicorn_conf.py`.
"""

import os

from prometheus_client import multiprocess


def on_starting(server):
    """Clear stale multiprocess metric files before any worker starts."""
    d = os.environ.get('PROMETHEUS_MULTIPROC_DIR')
    if d and os.path.isdir(d):
        for name in os.listdir(d):
            try:
                os.remove(os.path.join(d, name))
            except OSError:
                pass


def child_exit(server, worker):
    """Tell prometheus_client this worker's metrics are no longer live."""
    multiprocess.mark_process_dead(worker.pid)
