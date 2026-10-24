FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/ /app/backend/
WORKDIR /app/backend
RUN DJANGO_SECRET_KEY=build-only-not-a-runtime-secret DJANGO_DEBUG=0 python manage.py collectstatic --noinput
RUN mkdir -p /app/private-media && chmod 700 /app/private-media

CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 60"]
