FROM python:3.12-slim

WORKDIR /app

# curl: used by the internal service-discovery validation test and for debugging
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/service-c/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/service-c/ ./service-c/
COPY services/lib/ ./lib/

ENV PYTHONPATH=/app

WORKDIR /app/service-c

EXPOSE 3003

CMD ["gunicorn", "service_c.wsgi:application", "--bind", "0.0.0.0:3003", "--workers", "2"]