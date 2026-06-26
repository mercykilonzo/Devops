FROM python:3.12-slim

WORKDIR /app

COPY services/service-b/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/service-b/ ./service-b/
COPY services/lib/ ./lib/

ENV PYTHONPATH=/app

WORKDIR /app/service-b

EXPOSE 3002

CMD ["gunicorn", "service_b.wsgi:application", "--bind", "0.0.0.0:3002", "--workers", "2"]