# syntax=docker/dockerfile:1
# Standalone service — build context is this directory:
#   docker build -t aios-quality-platform .
FROM python:3.10-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd --system appuser && useradd --system --gid appuser --create-home --home-dir /home/appuser appuser

FROM base AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-warn-script-location -r requirements.txt

FROM base AS runtime
ENV PATH=/home/appuser/.local/bin:$PATH
COPY --from=builder /root/.local /home/appuser/.local
WORKDIR /app
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request as u,sys; sys.exit(0 if u.urlopen('http://127.0.0.1:8000/health/live',timeout=3).status==200 else 1)"
CMD ["uvicorn", "quality_platform.qa_api.application_factory:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
