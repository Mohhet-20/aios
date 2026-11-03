# syntax=docker/dockerfile:1
# This platform installs `aios-ai-core` as an editable sibling dependency
# (see requirements.txt: `-e ../aios-ai-core`), so the build context must be
# the AIOS monorepo root (the parent directory containing both
# `aios-ai-core/` and `aios-prompt-platform/`) — not this directory. Build with:
#   docker build -f aios-prompt-platform/Dockerfile -t aios-prompt-platform .
# (run from the monorepo root, one level above aios-prompt-platform/)
FROM python:3.10-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd --system appuser && useradd --system --gid appuser --create-home --home-dir /home/appuser appuser
WORKDIR /build

FROM base AS builder
COPY aios-ai-core/ ./aios-ai-core/
COPY aios-prompt-platform/ ./aios-prompt-platform/
RUN pip install --user --no-warn-script-location -r aios-prompt-platform/requirements.txt

FROM base AS runtime
ENV PATH=/home/appuser/.local/bin:$PATH
COPY --from=builder /root/.local /home/appuser/.local
# Editable install of aios-ai-core resolves to /build/aios-ai-core at import
# time, so that source tree must be present at the same absolute path here.
COPY --from=builder --chown=appuser:appuser /build /build
USER appuser
WORKDIR /build/aios-prompt-platform
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request as u,sys; sys.exit(0 if u.urlopen('http://127.0.0.1:8000/health/live',timeout=3).status==200 else 1)"
CMD ["uvicorn", "prompt_platform.main:app", "--host", "0.0.0.0", "--port", "8000"]
