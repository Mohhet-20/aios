# syntax=docker/dockerfile:1
# Hosted public demo API (render.yaml): all twenty AIOS services in one process on a 512 MB free instance.
# Build context: the repository root. The console runs as its own service from aios-frontend/Dockerfile.
#
# deploy/demo/combined.py imports each service's unmodified FastAPI app and serves it under /svc/<name> with the prefix
# stripped; each keeps its own SQLite database and enforces X-Internal-Token. demo_build.py seeds the demo organisation
# through the services' REST APIs at build time; demo_start.py copies that showcase fresh on every start.
# Measured: ~230 MB resident for all twenty. A real deployment runs each service from its own Dockerfile (docker-compose.yml, k8s/).

FROM python:3.11-slim AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY deploy/demo/requirements.txt /tmp/requirements.txt
COPY aios-ai-core /tmp/aios-ai-core
RUN pip install -r /tmp/requirements.txt && pip install /tmp/aios-ai-core

FROM python:3.11-slim AS base
COPY --from=deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 MALLOC_ARENA_MAX=2
WORKDIR /app
COPY . .

FROM base AS showcase
RUN python deploy/demo/demo_build.py && mkdir -p /app/showcase && cp -a /tmp/aios-demo/. /app/showcase/

FROM base AS runtime
COPY --from=showcase /app/showcase /app/showcase
RUN useradd --create-home --uid 1000 appuser
USER appuser
ENV AIOS_SHOWCASE_DIR=/app/showcase AIOS_DEMO_ROOT=/tmp/aios-demo
EXPOSE 8000
CMD ["python", "deploy/demo/demo_start.py"]
