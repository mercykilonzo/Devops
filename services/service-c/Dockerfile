FROM python:3.12.13-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/service-c/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/service-c/ ./service-c/
COPY services/lib/ ./lib/

ENV PYTHONPATH=/app

WORKDIR /app/service-c

ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc
RUN useradd --system --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /tmp/prometheus_multiproc \
    && chown -R appuser:appuser /app /tmp/prometheus_multiproc
USER appuser

EXPOSE 3003

CMD ["gunicorn", "service_c.wsgi:application", "-c", "/app/lib/gunicorn_conf.py", "--bind", "0.0.0.0:3003", "--workers", "2"]
