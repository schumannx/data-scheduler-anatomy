FROM python:3.12-slim

# Set at build time for blue/green image tags (release 02, 03, … over time).
ARG APP_RELEASE=local
LABEL org.opencontainers.image.version="${APP_RELEASE}"

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info"]
