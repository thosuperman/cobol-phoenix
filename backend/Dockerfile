# COBOL Phoenix backend (FastAPI). The backend never executes COBOL itself:
# it hands jobs to the network-less runner sidecar through a shared volume.
FROM python:3.13.17-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml ./
COPY phoenix ./phoenix
RUN pip install . && pip install "pytest==8.3.5"
COPY alembic.ini ./
COPY migrations ./migrations
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin phoenix \
 && mkdir -p /data /jobs && chown -R 10001:10001 /data /jobs
USER 10001
ENV PHOENIX_DATA_DIR=/data PHOENIX_COBOL_EXECUTOR=queue PHOENIX_QUEUE_DIR=/jobs
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn phoenix.api.main:app --host 0.0.0.0 --port 8000 --workers 1"]
