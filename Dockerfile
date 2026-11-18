ARG APP_UID=1000
ARG APP_GID=1000

FROM python:3.10-slim

ARG APP_UID
ARG APP_GID

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_RETRIES=5

# FFmpeg is required for audio export / merge.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

COPY . .

# Run the application as a dedicated, unprivileged UID/GID. Numeric ownership
# avoids requiring passwd/useradd in the slim image; bind-mounted host
# directories must be writable by this UID/GID (default 1000:1000).
RUN mkdir -p data run cache output logs uploads /home/app \
    && chown -R "${APP_UID}:${APP_GID}" data run cache output logs uploads /home/app \
    && chmod +x docker/entrypoint.sh

USER ${APP_UID}:${APP_GID}
ENV HOME=/home/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "/app/docker/healthcheck.py"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["--host", "0.0.0.0", "--port", "8000", "--strict-port"]
