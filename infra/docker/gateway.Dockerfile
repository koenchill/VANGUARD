# VANGUARD gateway image — lightweight AI gateway/API (Section 2 / G-008)

FROM python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93 AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY infra/docker/requirements/gateway.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock

FROM python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93 AS runner
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
COPY ./app /app/app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    VANGUARD_WORKLOAD=gateway
RUN useradd -u 8888 appuser && chown -R appuser:appuser /app /opt/venv
USER 8888
EXPOSE 8000
ENTRYPOINT ["python", "-m", "app.api.main"]
