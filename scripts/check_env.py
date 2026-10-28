#!/usr/bin/env python3
"""Verify the course environment.  `make check` runs this inside the container.

Every line is either `ok`, `warn` (you can continue, but something later will
bite), or `FAIL` (fix it before the lab). Each failure says how to fix it.
"""
from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
results: list[tuple[str, str, str]] = []


def record(status: str, what: str, detail: str = "") -> None:
    results.append((status, what, detail))


def check_python() -> None:
    v = sys.version_info
    ok = (v.major, v.minor) == (3, 12)
    record("ok" if ok else "FAIL", "Python 3.12", platform.python_version()
           + ("" if ok else " -- run inside the course container: make shell"))


def check_container() -> None:
    inside = os.environ.get("AIP2_IN_CONTAINER") == "1"
    record("ok" if inside else "warn", "running inside the course container",
           f"{platform.system()} {platform.machine()}" if inside else
           "you are on the host -- results may differ from everyone else's (Lab 8). Use: make shell")


def check_packages() -> None:
    wanted = {"numpy": "2.5.3", "pandas": "3.0.6", "sklearn": "1.9.1", "joblib": "1.6.0",
              "fastapi": "0.141.1", "pyarrow": "25.0.1", "dvc": None, "mlflow": None}
    for mod, pin in wanted.items():
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "?")
            if pin and ver != pin:
                record("FAIL", f"{mod} == {pin}", f"found {ver} -- make rebuild")
            else:
                record("ok", f"import {mod}", ver)
        except ImportError as exc:
            record("FAIL", f"import {mod}", f"{exc} -- make rebuild")


def check_data() -> None:
    p = ROOT / "data/claims/claims.parquet"
    record("ok" if p.exists() else "FAIL", "claims dataset",
           f"{p.stat().st_size / 1e6:.1f} MB" if p.exists() else "missing -- see START_HERE.md")


def check_docker() -> None:
    if not shutil.which("docker"):
        record("FAIL", "docker CLI", "not found -- make rebuild")
        return
    try:
        out = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"],
                             capture_output=True, text=True, timeout=15)
        if out.returncode == 0:
            record("ok", "docker engine reachable from inside", f"server {out.stdout.strip()}")
        else:
            msg = out.stderr.strip().splitlines()[-1] if out.stderr.strip() else "unknown error"
            hint = ("permission denied on the socket -- Linux host: run `make down && make up` "
                    "so DOCKER_GID is passed") if "permission" in msg.lower() else msg
            record("FAIL", "docker engine reachable from inside", hint)
    except subprocess.TimeoutExpired:
        record("FAIL", "docker engine reachable from inside", "timed out -- is Docker running?")


def check_git() -> None:
    def cfg(key: str) -> str:
        r = subprocess.run(["git", "config", "--get", key], capture_output=True, text=True, cwd=ROOT)
        return r.stdout.strip()
    name, email = cfg("user.name"), cfg("user.email")
    if name and email:
        record("ok", "git identity", f"{name} <{email}>")
    else:
        record("warn", "git identity", 'not set -- run once: git config --global user.name "Your Name" '
               '&& git config --global user.email you@example.com  (it persists)')


def check_ollama() -> None:
    host = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434").rstrip("/")
    try:
        with urllib.request.urlopen(f"{host}/api/version", timeout=3) as r:
            ver = json.load(r).get("version", "?")
        with urllib.request.urlopen(f"{host}/api/tags", timeout=3) as r:
            models = [m["name"] for m in json.load(r).get("models", [])]
        record("ok", "host Ollama reachable", f"v{ver}, {len(models)} model(s)")
    except Exception:  # noqa: BLE001
        record("warn", "host Ollama reachable",
               "not needed until Lab 14 (week 4). Then: install Ollama NATIVELY on your laptop "
               "(not in Docker -- it would lose the GPU) and run `ollama serve`")


def check_resources() -> None:
    free = shutil.disk_usage(ROOT).free / 1e9
    record("ok" if free > 10 else "warn", "free disk", f"{free:.0f} GB"
           + ("" if free > 10 else " -- Labs 9 and 15 build images; aim for 10 GB+"))
    try:
        mem = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9
        record("ok" if mem >= 6 else "warn", "memory available to Docker", f"{mem:.1f} GB"
               + ("" if mem >= 6 else " -- raise it in Docker Desktop > Settings > Resources"))
    except (ValueError, OSError):
        pass


def main() -> None:
    for fn in (check_container, check_python, check_packages, check_data,
               check_git, check_docker, check_ollama, check_resources):
        fn()
    width = max(len(w) for _, w, _ in results)
    for status, what, detail in results:
        tag = {"ok": "  ok  ", "warn": " warn ", "FAIL": " FAIL "}[status]
        print(f"[{tag}] {what:<{width}}  {detail}")
    fails = sum(1 for s, _, _ in results if s == "FAIL")
    print(f"\n{'Environment ready.' if not fails else f'{fails} problem(s) to fix before the lab.'}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
