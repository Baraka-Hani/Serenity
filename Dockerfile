FROM python:3.12-slim

WORKDIR /app

RUN groupadd --system serenity \
    && useradd --system --gid serenity --home-dir /nonexistent --shell /usr/sbin/nologin serenity \
    && mkdir /data \
    && chown serenity:serenity /data

COPY . .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ROAM_HOST=0.0.0.0 \
    ROAM_PORT=8765 \
    ROAM_DATA_DIR=/data

VOLUME ["/data"]
EXPOSE 8765
USER serenity

CMD ["python3", "backend/server.py"]
