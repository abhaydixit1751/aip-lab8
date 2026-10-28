# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# The AI in Practice 2 course environment.
#
# ONE image, identical on macOS, Windows and Linux, on ARM and on Intel/AMD.
# Lab 8 measured why this matters: the same pinned code produced different bits
# on macOS and Linux, while Linux containers on ARM and x86 agreed exactly.
#
# What is in here: Python 3.12, every course dependency from uv.lock, git, make,
# and the Docker CLI (so Labs 9 and 12 can build and run images from inside).
#
# What is deliberately NOT in here: the local LLM runtime. Inside Docker on a
# Mac a model cannot reach the GPU and runs ~10x slower (measured: 6.6 vs 66.6
# tokens/s). Ollama runs natively on the host; this container reaches it at
# http://host.docker.internal:11434 -- the same app-calls-model-server shape
# as production.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Docker CLI + buildx + compose: static Go binaries, safe to copy across libc.
COPY --from=docker:29-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:29-cli /usr/local/libexec/docker/cli-plugins /usr/local/libexec/docker/cli-plugins
COPY --from=ghcr.io/astral-sh/uv:0.7.15 /uv /usr/local/bin/uv

# libicu76: Lab 12 runs a GitHub Actions runner in here, and its config.sh refuses
# to start without ICU (measured; 37 MB). Everything else is for the labs' shell work.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git make curl ca-certificates less procps libicu76 \
 && rm -rf /var/lib/apt/lists/*

# The environment lives OUTSIDE the workspace, at /opt/venv. If it lived in
# /workspace/.venv it would collide with (or be hidden by) whatever the host
# has in its own copy of the repo -- including a macOS .venv that cannot run here.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /opt/build
COPY pyproject.toml uv.lock ./
# The cache mount keeps uv's download cache OUT of the image. Without it the
# cache is baked into this layer: measured 1.75 GB for a 933 MB environment.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-groups --no-install-project

# A non-root user with the most common Linux uid, so files created in the
# bind-mounted workspace are owned by the student on a Linux host.
#
# The environment stays owned by root and is READ-ONLY to the student, on
# purpose: a package change is a lockfile change plus `make rebuild`, never an
# ad-hoc `pip install` that makes one laptop differ from the other 26.
# (An earlier version ran `chown -R student /opt/venv` here. That copies every
# file into a new layer: measured +977 MB of pure duplicate.)
RUN useradd --create-home --uid 1000 --shell /bin/bash student

# On a Linux host whose user is not uid 1000, the bind-mounted repo is owned by
# a different uid and git refuses it ("dubious ownership"). The workspace is the
# student's own repo, so trust it. (Docker Desktop maps ownership; no effect there.)
RUN git config --system --add safe.directory '*'

# Measured trap: uv environments contain no pip, so a bare `pip install` falls
# through to the base image's system Python, reports success, and installs into
# ~/.local -- which the course environment never sees. "Installed" then
# "module not found". Replace the silent success with an explanation.
# Note: in the base image `pip` is a SYMLINK to `pip3`, so copying over `pip`
# silently overwrites `pip3` and leaves `pip3.12` untouched. Remove all three first.
RUN rm -f /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.12
COPY docker/bin/pip /usr/local/bin/pip
RUN cp /usr/local/bin/pip /usr/local/bin/pip3 && cp /usr/local/bin/pip /usr/local/bin/pip3.12

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    MLFLOW_DISABLE_AGENT_HINT=1 \
    PIP_REQUIRE_VIRTUALENV=1 \
    PYTHONNOUSERSITE=1 \
    OLLAMA_HOST=http://host.docker.internal:11434 \
    AIP2_IN_CONTAINER=1

USER student
WORKDIR /workspace
CMD ["bash"]
