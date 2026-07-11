"""OpenTelemetry tracing bootstrap, shared by all three services.

Called once per worker process from each service's `wsgi.py`, *before* the
Django application is created. It sets up a TracerProvider that exports OTLP
spans over HTTP to Jaeger, and turns on auto-instrumentation for:

  * Django  — creates a server span for every incoming request and extracts
    inbound W3C trace context (`traceparent`) so this service's spans join the
    caller's trace.
  * urllib  — injects `traceparent` into outgoing service-to-service calls made
    through `lib/http_client.py`, so context propagates across A → B → C → A.

Configuration comes from the standard OTEL env vars (set in docker-compose.yml):
    OTEL_SERVICE_NAME            e.g. "service-a"
    OTEL_EXPORTER_OTLP_ENDPOINT  e.g. "http://jaeger:4318"

`OTLPSpanExporter()` reads `OTEL_EXPORTER_OTLP_ENDPOINT` and appends the
`/v1/traces` signal path automatically.
"""

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.urllib import URLLibInstrumentor

_initialized = False


def init_tracing(default_service_name):
    """Initialise tracing for this process. Idempotent — safe to call twice."""
    global _initialized
    if _initialized:
        return

    service_name = os.environ.get("OTEL_SERVICE_NAME", default_service_name)
    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument()
    URLLibInstrumentor().instrument()

    _initialized = True
