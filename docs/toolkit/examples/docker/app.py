"""A tiny service for the Docker / compose / make primer. Not the claims service.

GET /health          liveness: the process is up
GET /ready           readiness: it can do its job (here: write to its data directory)
GET /hello/{name}    "<GREETING>, <name>", and how many times this name has visited

GREETING and DATA_DIR come from the environment, so the same image behaves
differently depending on how it is run: `docker run -e`, or compose's `environment:`.
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(title="primer-hello")


def data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    probe = data_dir() / ".ready"
    try:
        probe.write_text("ok")
    except OSError as e:  # e.g. a volume the non-root user cannot write to
        raise HTTPException(503, f"data directory not writable: {e}")
    return {"status": "ready", "greeting": os.environ.get("GREETING", "Hello")}


@app.get("/hello/{name}")
def hello(name: str) -> dict:
    counts_file = data_dir() / "visits.json"
    counts = json.loads(counts_file.read_text()) if counts_file.exists() else {}
    counts[name] = counts.get(name, 0) + 1
    counts_file.write_text(json.dumps(counts))
    greeting = os.environ.get("GREETING", "Hello")
    return {"message": f"{greeting}, {name}", "visits": counts[name]}
