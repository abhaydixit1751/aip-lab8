# AI in Practice 2 — everything runs in the course container.
# Works on macOS, Linux, and Windows (from a WSL2 terminal).

.PHONY: help up shell check down rebuild test mlflow clean

# On native Linux, pass the host's docker group id so the container can use the
# socket. Empty on macOS/Windows, where compose falls back to 0 (Docker Desktop).
DOCKER_GID ?= $(shell getent group docker 2>/dev/null | cut -d: -f3)
ifneq ($(DOCKER_GID),)
export DOCKER_GID
endif

help:
	@echo "make up       build (first time ~2 min) and start the course container"
	@echo "make shell    open a terminal inside it"
	@echo "make check    verify the environment, Docker access, and host Ollama"
	@echo "make test     run the test suite inside the container"
	@echo "make mlflow   MLflow UI at http://localhost:18500 (Ctrl-C to stop)"
	@echo "make down     stop the container"
	@echo "make rebuild  rebuild the image after uv.lock changes"

up:
	docker compose up -d --build dev
	@echo "\nReady. Next: make check"

shell:
	docker compose exec dev bash

check:
	docker compose exec dev python scripts/check_env.py

test:
	docker compose exec dev pytest -q tests

mlflow:
	docker compose exec dev mlflow ui --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --port 18500

down:
	docker compose down

rebuild:
	docker compose build --no-cache dev
	docker compose up -d dev
