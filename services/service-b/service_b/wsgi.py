import os
import sys

# Add services/ to path so the shared `lib` package is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_b.settings')

# Initialise OpenTelemetry before the app is built so Django/urllib get instrumented.
from lib.tracing import init_tracing  # noqa: E402
init_tracing('service-b')

from django.core.wsgi import get_wsgi_application  # noqa: E402
application = get_wsgi_application()
