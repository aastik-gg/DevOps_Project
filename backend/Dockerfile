# syntax=docker/dockerfile:1

# ---- build stage: resolve wheels into an isolated virtualenv ----
FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.txt .
RUN pip install -r requirements.txt \
    # pip is only needed to build; dropping it removes its vendored urllib3/msgpack CVEs from the image
    && pip uninstall -y pip setuptools wheel

# ---- runtime stage: no compilers, no pip cache, non-root ----
FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.title="gearloop-backend" \
      org.opencontainers.image.description="GearLoop lab equipment API (FastAPI)"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/venv/bin:$PATH
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* \
    && (python -m pip uninstall -y pip setuptools wheel || true) && rm -rf /usr/local/lib/python3.12/ensurepip \
    && groupadd --gid 10001 gearloop && useradd --uid 10001 --gid gearloop --no-create-home --shell /usr/sbin/nologin gearloop
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"
# Migrations are NOT run here: compose uses a one-shot `migrate` service and
# Helm uses a pre-install/pre-upgrade Job, so N replicas never race on Alembic.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
