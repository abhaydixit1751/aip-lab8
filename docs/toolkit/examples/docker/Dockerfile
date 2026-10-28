# syntax=docker/dockerfile:1
# The primer's example image: a tiny FastAPI service, packaged the way the
# course packages services. Multi-stage, dependencies exactly as uv.lock pins
# them, non-root, with a HEALTHCHECK.
#
#   docker build -t aip2-primer-hello:1 .                 # the runtime image (last stage)
#   docker build --target test -t aip2-primer-hello:test .

# ---- stage 1: build the environment (tools live here, and stay here) --------
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.7.15 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /build
# The lockfile first, the code later: a code edit then reuses this layer.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---- stage 2: tests (only built when asked for: --target test) --------------
FROM builder AS test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /src
COPY app.py ./
COPY tests/ tests/
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"]

# ---- stage 3: runtime (the default: the last stage is the image) ------------
FROM python:3.12-slim AS runtime
# A user with no special rights, and a data directory it owns. A named volume
# mounted at /data starts with this ownership; anywhere else it is root's.
RUN useradd --uid 10001 --no-create-home app \
 && mkdir /data && chown app /data
# Same path as in the builder: the venv's scripts have /opt/venv baked in.
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data
WORKDIR /srv
COPY app.py ./
USER app
EXPOSE 8000
# slim has no curl: ask Python. Exit code 0 = healthy. During the start period
# it checks every second (--start-interval), afterwards every 5 s.
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --start-interval=1s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2)"]
# Exec form (a JSON list): uvicorn is PID 1 and receives `docker stop`'s SIGTERM.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
