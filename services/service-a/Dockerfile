FROM python:3.12.13-slim

WORKDIR /app

COPY services/service-a/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/service-a/ ./service-a/
COPY services/lib/ ./lib/

ENV PYTHONPATH=/app

WORKDIR /app/service-a

# Run as a non-root user (gunicorn's control socket needs a writable HOME).
RUN useradd --system --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 3001

CMD ["gunicorn", "service_a.wsgi:application", "--bind", "0.0.0.0:3001", "--workers", "2"]