FROM python:3.12-slim

WORKDIR /app

# curl: used by the internal service-discovery validation test and for debugging
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/service-a/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/service-a/ ./service-a/
COPY services/lib/ ./lib/

ENV PYTHONPATH=/app

WORKDIR /app/service-a

EXPOSE 3001

CMD ["gunicorn", "service_a.wsgi:application", "--bind", "0.0.0.0:3001", "--workers", "2"]