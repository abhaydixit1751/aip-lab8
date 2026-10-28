# AI in Practice 2 — start here

**Everything runs in one container.** The same image on macOS, Windows and
Linux, on Apple Silicon and on Intel/AMD. You install Docker and a handful of
small host tools (§1); Python, every library, and every ML tool come pinned
inside the container.

Why it matters: in Lab 8 the same pinned code produced **different bits on
macOS and on Linux** — the operating system's maths libraries differ even when
every Python package is identical. Inside the course container, every one of
you gets the **same model, bit for bit** (verified on ARM and on x86).

Do this **before week 1**, not in the lab room. It takes about 15 minutes.

---

## 1 · Install Docker

| Your laptop | Install |
|---|---|
| **macOS** | [Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| **Windows** | Docker Desktop with the **WSL 2** backend — then read the Windows notes below |
| **Linux** | Docker Engine + the Compose plugin from your distribution or docs.docker.com |

Docker Desktop is free for enrolled students under Docker Personal.

Then in Docker Desktop → **Settings → Resources**: give Docker **at least 6 GB
of memory**, and keep **10 GB of disk** free.

### 1b · The host tools

A few things run on your laptop, outside the container: `git` (your team
repository lives on the laptop), `make`, `unzip`, the GitHub CLI `gh` (to log
in to GitHub; it refuses passwords), and from Lab 10, Node.js 20 or later for
the coding agents.

| Your laptop | Install |
|---|---|
| **macOS** | `xcode-select --install` (gives `git` and `make`; `unzip` is built in), then `brew install gh node` |
| **Windows (WSL 2 Ubuntu)** | `sudo apt update && sudo apt install -y git make unzip gh`; Node.js 20+ from nodejs.org or `nvm` |
| **Linux** | the same packages from your distribution |

Then set your git identity **on the laptop** and log in to GitHub, once:
[`docs/toolkit/git-and-github.md`](docs/toolkit/git-and-github.md) §1–2.
New to any of these tools? [`docs/toolkit/`](docs/toolkit/README.md) has a
short primer for each, with the commands this course actually uses.

## 2 · Start the course environment

In a terminal, in this folder:

```bash
make up       # first time: builds the image, ~2 minutes
make check    # every line should say ok
```

Expected:

```
[  ok  ] running inside the course container  Linux aarch64   (or x86_64)
[  ok  ] Python 3.12                          3.12.14
[  ok  ] import sklearn                       1.9.1
...
[  ok  ] docker engine reachable from inside  server 29.x
[ warn ] host Ollama reachable                not needed until Lab 14 (week 4)
Environment ready.
```

## 3 · Work inside it

Pick one:

- **VS Code or Cursor** (recommended): open this folder → *Reopen in Container*.
  Your editor, terminal and Python all run inside the course environment.
- **Terminal:** `make shell` opens a shell inside it. Edit files on your laptop
  as normal — the folder is shared.

Everything else in the course assumes you are **inside**. If a command behaves
oddly, the first question is always: *am I in the container?* (`make check`
says so on its first line.)

---

## Rules of the environment

**`pip install` is switched off, on purpose.** The environment is identical on
all 27 laptops because it is built from `uv.lock`. To add a package: add it to
`pyproject.toml`, run `uv lock`, then `make rebuild`. (If you try `pip`, it
explains this. Without the block, `pip` would report success and install into a
Python the course never uses — "installed", then "module not found".)

**Course services use ports 18xxx**, not 8000/8080/5000 — those are the most
crowded ports in development and probably taken by something else on your
laptop. The MLflow UI is at <http://localhost:18500>.

**A container you start from inside the course container runs on your laptop.**
From your browser it is `localhost:18001`. From *inside* the course container,
`localhost` means the course container itself — use
`http://host.docker.internal:18001` instead. (This will trip you in Lab 9.)

---

## What is NOT in the container: the local LLM (from week 4)

In Labs 14–15 you run open models on your own laptop with **Ollama**. Install it
**natively**, not in Docker:

| | Output speed, same model and prompt |
|---|---|
| Ollama native on a Mac (GPU) | 66.6 tokens/s |
| Ollama inside Docker on a Mac (CPU only) | 6.6 tokens/s — **10× slower** |

Docker on a Mac cannot reach the GPU. So Ollama runs on your laptop and the
course container calls it at `http://host.docker.internal:11434` — which is how
production systems are built anyway: the application container calls a separate
model server. Setup instructions arrive with Lab 14.

---

## Windows notes — read these, they save an afternoon

1. **Work inside WSL 2.** Open the *Ubuntu* terminal (installed with WSL) and
   clone the repository into your Linux home, e.g. `~/aip2`. Do **not** keep
   the repository on `C:\` — a Windows folder shared into a Linux container is
   many times slower.
2. Run `make up`, `make check` etc. **from the Ubuntu terminal.** Your Windows
   Downloads folder is `/mnt/c/Users/<you>/Downloads` there, not `~/Downloads`:
   `unzip /mnt/c/Users/<you>/Downloads/AI-in-Practice-2-Week2.zip -d .`
3. In VS Code: install the *WSL* extension, open the folder from WSL, then
   *Reopen in Container*.
4. Line endings are handled for you by `.gitattributes`. If you ever see
   `/bin/sh^M: bad interpreter`, a file was saved with Windows line endings.

## Linux notes

- Add yourself to the `docker` group (`sudo usermod -aG docker $USER`, then log
  out and in).
- `make up` detects your docker group automatically. If `make check` reports
  *permission denied on the socket*, put `DOCKER_GID=<gid of the docker group>`
  in `.env` and run `make down && make up`.

---

## If something goes wrong

| Symptom | Fix |
|---|---|
| `make: command not found` (Windows) | You are in PowerShell. Use the Ubuntu (WSL) terminal |
| `Cannot connect to the Docker daemon` | Start Docker Desktop |
| `port is already allocated` | Something on your laptop uses that port. Set e.g. `MLFLOW_PORT=18501` in `.env` |
| `make check`: a package version FAILs | `make rebuild` |
| Build is extremely slow on Windows | The repo is on `C:\`. Move it into WSL (note 1) |
| Anything else | Run `make check` and paste its output on the course channel |
