# Docker, compose and make: a working primer

**Who needs this.** Lab 9 onward. Lab 9 has you write a Dockerfile by hand,
Lab 12 tags and pushes images, Lab 15 hands you a compose file with profiles
and internal networks, and the capstone needs all of it: a `Dockerfile`, a
`compose.yaml` and a `Makefile` with `make up / test / eval / gate-break /
down`. Until now you have used Docker as `make up`. This page explains what
that command was doing, and how to write your own.

> **The minimum**
>
> - An **image** is a read-only template; a **container** is one running copy of it.
> - `docker build -t NAME:TAG .` builds an image from `./Dockerfile`; the trailing `.` is the **context**.
> - `docker run -d --name X -p HOST:CONTAINER IMAGE` starts a container; the **laptop** port is on the **left**.
> - `docker compose up -d` starts every service in `compose.yaml`; `docker compose down` stops them.
> - A Makefile recipe line starts with a **TAB**. Every target that is a command belongs in `.PHONY`.
> - Inside the course container, `localhost` is the course container. Your services are at `host.docker.internal`.

Everything below was run on an Apple Silicon Mac, Docker Engine 29.8.0,
Docker Compose 5.5.1, GNU Make 3.81 on the Mac and 4.4.1 in the course image.
The numbers are from those runs. Anything not run is marked **(not run here)**.

**The worked example** is a tiny FastAPI service in [`examples/docker/`](examples/docker/),
deliberately not the claims service. `app.py` answers `/health`, `/ready` and
`/hello/{name}` with a greeting from `GREETING` and a visit counter in `DATA_DIR`;
`uv.lock` pins fastapi and uvicorn as the course does. Beside them: a
multi-stage `Dockerfile` with an allowlist `Dockerfile.dockerignore`, three unit
tests, a five-case `eval/`, a `compose.yaml` and a `Makefile` with the capstone targets.

The course's own working Dockerfile is [`docker/dev.Dockerfile`](../../docker/dev.Dockerfile):
read it after section 4. Every comment in it is a measured decision.

## 1 · Images, containers, layers, the build context

Lab 9's [CONCEPTS](../../labs/lab09/CONCEPTS.md) ("What an image is", "The
build context") explains these properly. The short version:

- An **image** is a stack of read-only **layers**, one per `COPY`, `RUN` or
  `ADD`. Deleting a file in a later layer does not shrink the image.
- A **container** is an image plus a thin writable layer and a process. Remove
  the container and that layer goes too: data that must survive lives in a **volume**.
- The **build context** is the folder you hand to `docker build`: all of it is
  sent to the engine, and only its files can be `COPY`'d.
- The **engine** (daemon) does the work; `docker` is only a client. In the
  course container it talks to your laptop's engine through
  `/var/run/docker.sock`, so containers it starts run **on the laptop**.

## 2 · `docker run` and its friends

```bash
docker run -d --name aip2-primer-hello -p 18910:8000 aip2-primer-hello:1
```

| Flag | Meaning |
|---|---|
| `-d` | detached: start it in the background and print its ID |
| `--rm` | remove the container when it exits (for one-off commands) |
| `--name X` | a name you choose; otherwise Docker invents one (`zealous_hopper`). Names are unique: a second `--name X` fails until the first is removed |
| `-p 18910:8000` | **HOST:CONTAINER**. Port 18910 on the laptop forwards to port 8000 inside. The app always listens on 8000; you choose the laptop side at run time |
| `-e GREETING=Namaste` | set an environment variable inside the container |
| `-v NAME:/data` | mount a **named volume** (Docker manages it; it outlives the container) |
| `-v /abs/path:/data:ro` | a **bind mount**: a folder of the laptop appears inside. `:ro` = read-only |
| `--entrypoint id` | replace the image's `ENTRYPOINT` for this run (section 4) |
| `-it` | `-i` keep stdin open, `-t` give it a terminal: for an interactive shell |

Anything after the image name replaces the image's `CMD`:

```bash
docker run --rm aip2-primer-hello:1 python -c "import fastapi; print(fastapi.__version__)"   # 0.141.1
docker run --rm --entrypoint id aip2-primer-hello:1 -u                                       # 10001: not root
docker run --rm -it aip2-primer-hello:1 bash          # a shell inside; exit with Ctrl-D
```

**Looking at running containers.**

```bash
docker ps                                   # running ones; -a adds stopped ones
docker ps --filter name=aip2-primer         # NAMES  STATUS  Up 5 seconds (healthy) ...
docker logs aip2-primer-hello               # its stdout/stderr; -f follows, --tail 20
docker exec aip2-primer-hello id            # run a command INSIDE the running container
docker exec -it aip2-primer-hello bash      # a shell inside it
docker stop aip2-primer-hello               # SIGTERM, then SIGKILL after a timeout
docker rm -f aip2-primer-hello              # stop and remove in one go
```

**`docker inspect`** prints everything Docker knows about a container as
JSON. `--format` picks one field with Go template syntax:

```bash
docker inspect --format '{{.State.Health.Status}}' aip2-primer-hello              # healthy
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' aip2-primer-hello   # one variable per line
docker inspect --format '{{json .NetworkSettings.Ports}}' aip2-primer-hello
docker inspect --format '{{json .State.Health}}' aip2-primer-hello   # the last health checks, with their output
```

The second line is the answer to Lab 13's "check `docker inspect` for
`OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`": list the environment, then `grep`.

**Images and disk.**

```bash
docker image ls aip2-primer-hello      # tags, ID, size
docker history aip2-primer-hello:1     # each layer and its size: where the megabytes are
docker system df                       # images, containers, volumes, build cache: total and reclaimable
```

Docker Desktop's `image ls` shows *disk usage* (unpacked: 225 MB for the
example) and *content size* (compressed, what a push sends: 48.7 MB).

**Named volume vs bind mount, measured.** With `-v aip2-primer-visits:/data`,
`docker rm -f` and a fresh `docker run` on the same volume, the visit count
went 1, then 2: the data outlived the container. Without a volume it starts
again at 1. A bind mount shows a laptop folder; use it for what lives in the
repo (code, an evaluation set), and named volumes for what the service writes.

**A one-off shell on a volume.** Lab 13's `docker run --rm -v aip2-prod-predictions:/p
nginx:1.29-alpine sh -c 'rm -f /p/*.jsonl'` borrows nginx only for its shell: `-v` puts the
volume at `/p`, `--rm` throws the container away. It deletes data; read it twice.

## 3 · `docker build`

```bash
docker build -f Dockerfile -t aip2-primer-hello:1 .
```

| Part | Meaning |
|---|---|
| `-f FILE` | which Dockerfile. Default: `Dockerfile` in the context |
| `-t NAME:TAG` | the name to give the result. Without `:TAG` you get `:latest` |
| `.` | **the context**: the folder whose files `COPY` can see. Not optional, and not the Dockerfile's folder unless you say so |
| `--no-cache` | rebuild every layer; for honest build times |
| `--progress=plain` | full log of every step, instead of the collapsing display |
| `--target NAME` | build only up to the stage `FROM ... AS NAME` |

`COPY` paths are relative to the context, never to the Dockerfile. From the
repo root, the example builds with `docker build -f
docs/toolkit/examples/docker/Dockerfile -t aip2-primer-hello:1
docs/toolkit/examples/docker`. Give it `.` (the repo root) instead and it
fails: `"/app.py": not found`. There is no `app.py` at the root.

**`.dockerignore`.** A file named `Dockerfile.dockerignore` next to the
Dockerfile filters the context (a root `.dockerignore` does the same for every
Dockerfile). Write it as an allowlist: the example's is `*` (ignore everything),
then `!pyproject.toml`, `!uv.lock`, `!app.py`, `!tests/`, one per line.
Measured: context 24.98 kB, almost all of it `uv.lock`. A one-stage version
with no ignore file (`COPY . .`) shipped the Dockerfile, `tests/` and `eval/`
inside the image, ran as root, and was 280 MB against 225 MB.

**Build times.** First build 30.1 s (17 s of it fetching and unpacking the
base); `--no-cache` 3.1 s; after editing `app.py` 1.0 s, dependencies `CACHED`.

> **The base tag moved under us.** `docker image ls` showed `python:3.12-slim`
> as Python 3.12.13, yet the build used 3.12.15: `docker build` asks the
> registry what a tag means *now* (the `load metadata` step). A tag is a
> pointer. For the same base on every build, pin a digest:
> `FROM python:3.12-slim@sha256:...`.

## 4 · Writing a Dockerfile

| Instruction | Does | Example |
|---|---|---|
| `FROM image AS name` | start a stage from a base image; `AS` names it | `FROM python:3.12-slim AS builder` |
| `WORKDIR /path` | `cd`, creating it if needed; later relative paths start here | `WORKDIR /srv` |
| `COPY src dest` | context to image. `--from=stage` copies from another stage or image instead | `COPY --from=builder /opt/venv /opt/venv` |
| `RUN cmd` | run a command at **build** time; its file changes become a layer | `RUN useradd --uid 10001 app` |
| `ENV K=V` | set an environment variable for later steps **and** for the running container | `ENV PATH="/opt/venv/bin:$PATH"` |
| `USER name` | later `RUN`s and the container's process run as this user | `USER app` |
| `EXPOSE 8000` | documentation only: publishes nothing. `-p` does that | |
| `HEALTHCHECK ... CMD ...` | a command Docker runs inside, on a schedule; exit 0 = healthy | see below |
| `CMD [...]` | the default command; anything after the image name in `docker run` replaces it | `CMD ["uvicorn", "app:app", ...]` |
| `ENTRYPOINT [...]` | the fixed program; `CMD` then supplies its default arguments. Replaced only by `--entrypoint` | |

The example [`Dockerfile`](examples/docker/Dockerfile), shortened. A comment must be on a line of its own:
after an instruction, `#` is more arguments (`COPY a.txt /a.txt  # the file` failed: `"/#": not found`).

```dockerfile
# ---- stage 1: build the environment ---------------------------------------
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.7.15 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /build
# (1) the lockfile first; (2) exactly what uv.lock pins
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---- stage 2: tests, built only with --target test (see the file) ----------

# ---- stage 3: runtime (the last stage is the image) -------------------------
FROM python:3.12-slim AS runtime
# (5) a non-root user that owns its data directory
RUN useradd --uid 10001 --no-create-home app \
 && mkdir /data && chown app /data
# (3) the SAME path as in the builder; (4) its bin/ on PATH
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 DATA_DIR=/data
WORKDIR /srv
COPY app.py ./
USER app
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --start-interval=1s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2)"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**The uv pattern, point by point.**

1. **`pyproject.toml` and `uv.lock` before the code.** The expensive layer
   (the install) depends only on them, so a code edit reuses it: 1.0 s rebuilds.
2. **`uv sync --frozen`** installs exactly what the lockfile says and fails if
   the lockfile is out of date, instead of quietly re-resolving. `--no-dev`
   leaves out the `dev` group; `--no-install-project` installs dependencies
   only (the code arrives by `COPY`). The course's own `pyproject.toml` has
   `default-groups`, so Lab 9's flags differ: Lab 9 CONCEPTS, "The dependency groups".
3. **The same venv path in both stages.** The venv's scripts name their
   interpreter by absolute path: `head -1 /opt/venv/bin/uvicorn` prints
   `#!/opt/venv/bin/python`. Copied to `/app/venv` instead, the container
   died with `exec /app/venv/bin/uvicorn: no such file or directory`, about a
   file that is there. (What is missing is the interpreter named on its first line.)
4. **`ENV PATH`.** Without it, `uvicorn` is not found: `exec: "uvicorn":
   executable file not found in $PATH`, exit 127.
5. **Non-root.** `docker run --rm --entrypoint id aip2-primer-hello:1 -u`
   prints `10001`. Create anything the user must write (here `/data`) and
   `chown` it **before** `USER`. Never `chown -R` a whole environment: the
   course image measured that at +977 MB.

**Multi-stage.** Only the stage you build becomes the image, by default the
last. `uv`, its cache and the `test` stage's pytest stay behind. Measured:
runtime 225 MB, test image 300 MB, one-stage version 280 MB. `docker
history` shows the runtime's own layers: 17.3 MB of venv and 12 kB of app on
top of the base. A plain `docker build` skipped the `test` stage entirely.

**`HEALTHCHECK`.** slim has no `curl` (`sh: 1: curl: not found`), so ask
Python. Health checks run every `--interval`, and the first one waits for it:
with `--interval=5s` alone the container answered `/ready` at 0.4 s but was
reported `healthy` only at 5.4 s. `--start-interval=1s` (checks every second
during the start period) brought that to 1.21–1.25 s over 3 runs. Failures
inside `--start-period` do not count; after it, `--retries` failures in a row
mean `unhealthy`.

**`CMD` vs `ENTRYPOINT`, exec vs shell form.** Use `CMD` alone for a
service image: it is easy to replace (`docker run IMAGE python -c ...`). Use
the **exec form** (a JSON list). The shell form, `CMD uvicorn app:app ...`,
runs `/bin/sh -c "..."` as process 1, and the shell does not pass on
`docker stop`'s SIGTERM. Measured: exec form stopped in 0.36 s, exit 0;
shell form was killed after the stop timeout, 3.1 s here, exit 137 (SIGKILL).

**Lab 9** follows this pattern, not this file (other dependencies, flags and
files). It is written by hand: read the example, do not paste it.

## 5 · Tag and push to a registry

A **registry** stores images by name and tag; Docker Hub is one, Lab 12's
`localhost:18050` is another (the `registry:3` image). The image's name says
where it goes: `localhost:18950/aip2-primer-hello:ed6e1df31d97` means
registry `localhost:18950`, repository `aip2-primer-hello`, tag `ed6e1df31d97`.

```bash
docker run -d --name aip2-primer-registry -p 18950:5000 registry:3   # a throwaway registry
TAG=$(git rev-parse HEAD | cut -c1-12)                              # first 12 characters of the commit
docker tag aip2-primer-hello:1 localhost:18950/aip2-primer-hello:$TAG   # a second name, no copy
docker push localhost:18950/aip2-primer-hello:$TAG                     # 0.8 s; 4 layers "Pushed"
curl -s localhost:18950/v2/aip2-primer-hello/tags/list
#  {"name":"aip2-primer-hello","tags":["ed6e1df31d97"]}
docker pull localhost:18950/aip2-primer-hello:$TAG                     # anyone who can reach it
```

Pushing the same image under a second tag sent nothing new (`Layer already
exists`); after `docker image rm` and `docker pull` the image ID was the same,
`160eb3c83457`. In CI (Lab 12) `$GITHUB_SHA` is the full commit hash: in bash
`${GITHUB_SHA::12}` gives the first 12 characters. Never tag `latest`: a tag
must name one build. Docker allows plain HTTP to registries on `localhost`.

## 6 · docker compose

A `compose.yaml` writes down the `docker run` commands of a whole system, so
`docker compose up` runs them together. The example's
[`compose.yaml`](examples/docker/compose.yaml), with the course files beside it:

| Key | What it says | In the example | In the course |
|---|---|---|---|
| `name:` | the **project name** | `aip2primer` | `aip2` (`compose.yaml`), `aip2-airgap` (Lab 15) |
| `services:` | one entry per container | `api`, `test`, `evaluate` | `dev`; `aurora`, `egress`, `gateway`, `eval-*` |
| `build:` | `context`, `dockerfile`, `target`: as `docker build` | `context: .`, `target: runtime` | `target: eval` (Lab 15) |
| `image:` | the tag for what it builds, or the image to run if no `build:` | `aip2-primer-hello:dev` | `nginx:1.29-alpine` |
| `ports:` | `"HOST:CONTAINER"`, as `-p` | `"${API_PORT:-18910}:8000"` | `"18100:8000"` |
| `environment:` | as `-e`; `${VAR:-default}` comes from your shell or `.env` | `GREETING: ${GREETING:-Hello}` | `OLLAMA_HOST: ...` |
| `env_file:` | every line of a file, into the container | `.env`, `required: false` | the same |
| `volumes:` | `name:/path` named, `./path:/path` bind | `visits:/data`, `./eval:/eval:ro` | `home:/home/student`, `.:/workspace` |
| `depends_on:` | start order; with `condition: service_healthy`, waits for the healthcheck | `evaluate` waits for `api` | `aurora` after `gateway` |
| `networks:` | which networks a service joins; `internal: true` has no way out | `front`, `back` (internal) | `airgap` (internal), `outside` |
| `profiles:` | the service starts only when its profile is asked for | `test`, `eval` | `eval` (Lab 15) |
| `command:` | replaces the image's `CMD` | `python /eval/evaluate.py ...` | `sleep infinity` |

**Project names and prefixes.** Compose prefixes everything it creates with
the project name: containers `aip2primer-api-1` (project, service, number),
networks `aip2primer_back` and volumes `aip2primer_visits` (project,
underscore, name). That is why Lab 15's internal network is
`aip2-airgap_airgap` and its container `aip2-airgap-aurora-1`. Find the real
names with `docker network ls` and `docker volume ls`. `-p other` changes the
project: `docker compose -p aip2primer2 up` started a second, separate copy
(`aip2primer2-api-1`, its own network and volume).

**`.env` does two jobs.** Measured, with `GREETING=Vanakkam` and
`EXTRA_NOTE=...` in `.env`: `${GREETING}` in `compose.yaml` became
`Vanakkam` (interpolation), and `EXTRA_NOTE` reached the container only
because of `env_file:`. A variable in your shell beats `.env`:
`GREETING=Salaam docker compose up -d` gave `Salaam`. Compose reads the
`.env` next to the compose file, not the one in your current folder
(measured), so `-f labs/lab15/...` skips the root `.env`. `docker compose config`
shows what compose will actually run.

**Profiles.** `docker compose up` ignores `test` and `evaluate`; `docker
compose config` does not even list them. Ask for them by name:
`docker compose --profile eval run --rm evaluate`. That is Lab 15's
`dc --profile eval run --rm eval-local`.

**Internal networks, measured.** `evaluate` sits only on `back`
(`internal: true`): it reached `http://api:8000/ready` by **service name**,
and a request to `https://pypi.org` failed with `Temporary failure in name
resolution`. `api` is also on `front`, so it can publish a port and reach out.

**The commands.**

```bash
docker compose up -d --build --wait api   # build if needed, start, wait until healthy (4.8 s, warm)
docker compose ps                         # NAME aip2primer-api-1 ... Up 16 seconds (healthy)
docker compose logs --tail 3 api          # -f to follow
docker compose exec api id                # inside the running service: uid=10001(app)
docker compose --profile eval run --rm evaluate   # a one-off container of a service, then removed
docker compose down                       # remove containers and networks; volumes stay (visits 7, then 8)
docker compose down -v                    # ... and the volumes: the data is gone (visits back to 1)
```

> **A trap measured while building `gate-break`.** `GREETING=Hullo docker
> compose up -d api`, then `docker compose --profile eval run --rm evaluate`
> without `GREETING` set: `run` saw `api`'s configuration had changed
> (Hello, not Hullo), **recreated it**, and the gate passed. The break was
> undone silently. Every compose command must see the same variables.

## 7 · make

`make` runs named recipes. A **Makefile** is a list of rules:

```make
target: prerequisites
<TAB>command
```

Run `make target`, or `make` alone for the first target. Things to know:

| | |
|---|---|
| **TAB** | recipe lines start with a TAB character, not spaces. Spaces give `Makefile:2: *** missing separator.  Stop.` |
| one shell per line | `cd x` on one line is forgotten on the next. Join lines with `; \` to share a shell |
| `@` | do not echo the command (`@echo ...`) |
| `-` | ignore this line's failure and carry on |
| a failure stops make | a non-zero exit ends the run; `make` exits 2 |
| `VAR := value` | a variable, used as `$(VAR)`. `VAR ?= value` sets it only if not already set: `make gate GATE_MIN=0.8` overrides |
| `$$` | a literal `$` for the shell: `$$status`, `$$?` |
| `$(MAKE)` | call make again (sub-make), passing your flags |
| `make -n target` | print what would run, run nothing. Exception: lines containing `$(MAKE)` still run, in dry-run mode |

**`.PHONY`, and the trap in this course.** `make` was built to make files: a
target is "up to date" if a **file or directory** of that name exists and is
newer than its prerequisites. The capstone has an `eval/` directory and an
`eval` target. Reproduced with both makes:

```
$ make eval            # no .PHONY, eval/ exists
make: `eval' is up to date.            (make 3.81, macOS)
make: 'eval' is up to date.            (make 4.4.1, the course image)
```

Exit code 0, nothing ran. With `.PHONY: eval` it ran. The fix: list every
command-target in `.PHONY`. Lab 20's clean-clone rehearsal met exactly this.

**Reading the course [`Makefile`](../../Makefile).** `.PHONY` lists every
target. `DOCKER_GID ?= $(shell getent group docker ...)` runs a shell command
when the Makefile is read (empty on macOS), and `ifneq` exports it only if it
is set. `up` is `docker compose up -d --build dev`; `shell` is `docker compose
exec dev bash`; `rebuild` is `build --no-cache` then `up`. Each target is one
or two compose commands with a name you can remember.

**The capstone shape.** The example [`Makefile`](examples/docker/Makefile)
is the generic version, shortened (your recipes will differ):

```make
.PHONY: help up test eval gate gate-break down
COMPOSE  := docker compose
GATE_MIN ?= 1.0

up:
	$(COMPOSE) up -d --build --wait api
test:
	$(COMPOSE) --profile test run --rm --build test
eval:
	$(COMPOSE) --profile eval run --rm evaluate
gate:
	$(COMPOSE) --profile eval run --rm evaluate \
	  python /eval/evaluate.py --url http://api:8000 --min $(GATE_MIN)
gate-break:
	GREETING=Hullo $(MAKE) --no-print-directory up gate; status=$$?; \
	$(MAKE) --no-print-directory up; \
	exit $$status
down:
	$(COMPOSE) down
```

`gate-break` applies a deliberate regression **through configuration**, not
by editing a file, runs the gate, **always** restores the service, and exits
with the gate's status. Red is the point. Measured, from the example folder:

| Target | Time | Result |
|---|---|---|
| `make up` (image already built) | 4.8 s | `aip2primer-api-1 Healthy` |
| `make test` | 1.9 s | `3 passed` (and a harmless `StarletteDeprecationWarning`) |
| `make eval` | 0.96 s | `cases=5 accuracy=1.00 p50_ms=0.8` |
| `make gate` | 0.99 s | `gate: accuracy 1.00 >= 1.00? PASS`, exit 0 |
| `make gate-break` | 7.2 s | `accuracy 0.00 ... FAIL`, service restored, `make: *** [gate-break] Error 2` |

The break is a whole-greeting change, so it fails every case. Lab 20's
reference broke a single bound and the gate **passed**: no evaluation case sat
near it. A break your gate cannot see means your evaluation set needs a case,
not that the gate is fine.

## 8 · Where `localhost` is

| You are in | `localhost` means | To reach a container published with `-p 18910:8000` | To reach the laptop's Ollama |
|---|---|---|---|
| a laptop terminal or browser | the laptop | `localhost:18910` | `localhost:11434` |
| the course container | the course container | `host.docker.internal:18910` | `host.docker.internal:11434` |
| the service container itself | that container | `127.0.0.1:8000` (what `HEALTHCHECK` uses) | `host.docker.internal:11434` |
| another service in the same compose project | that container | `api:8000`: the service name, the container port | as above |

**Why `docker push localhost:18050/...` works from inside the course
container**, when `curl localhost:18050` from there fails. The `docker` command
only forwards the request; the **engine on the laptop** does the push, and for
the engine `localhost` is the laptop, where the registry listens. Measured
from a container holding the laptop's socket: `wget localhost:18950` was
refused, `wget host.docker.internal:18950` answered, and `docker push
localhost:18950/aip2-primer-hello:...` succeeded.

**The same rule bites bind mounts.** In `./eval:/eval` the left side is
resolved by the **engine**, as a laptop path. Run from inside a container, the
path it sends is the container's own (`/workspace/...`). Measured on macOS:
`mounts denied: The path /workspace/.../eval is not shared from the host and
is not known to Docker`. On Linux the engine instead creates an empty folder
and your service sees nothing **(not run here)**. So run `make` for a
compose project with bind mounts from a **laptop** terminal (macOS: `make`
comes with the Xcode Command Line Tools; WSL: `sudo apt install make`).
`docker build` and `docker run` without bind mounts work from either.

## Try it (15 minutes)

From a laptop terminal, in `docs/toolkit/examples/docker/`:

1. **Build and look.** `docker build -t aip2-primer-hello:1 .`, then `docker
   history aip2-primer-hello:1`. Which layers are yours, and how big are they?
2. **Run and call it.** `docker run -d --name aip2-primer-hello -p 18910:8000
   aip2-primer-hello:1`; `docker ps` until `(healthy)`; `curl
   localhost:18910/hello/Asha` twice. Check the user: `docker exec
   aip2-primer-hello id`.
3. **Break one thing.** Pick one:
   - Copy the venv to `/app/venv` in the runtime stage (keep `ENV PATH` as is).
     Rebuild, run, read the error. Why "no such file", for a file that exists?
   - Start a second container with `-p 18910:8000`. Read the error, then
     `docker ps -a`: what state did it leave behind?
   - Mount a volume at a path the image did not prepare:
     `-e DATA_DIR=/state -v aip2-primer-state:/state`. Watch `docker ps` go
     from `health: starting` to `unhealthy` (20.9 s here) and find the reason
     with `docker inspect --format '{{json .State.Health}}'`.
4. **Fix it** and say in one sentence what the fix changed.
5. **The stack.** `docker rm -f aip2-primer-hello`, then `make up`, `make test`,
   `make eval`, `make gate-break`. Delete `.PHONY`, run `make eval`, put it back.
6. **Clean up.** `docker compose down -v`; `docker rm -f` every `aip2-primer-*`
   container; `docker volume rm aip2-primer-state`; `docker image rm` your tags.

## If it goes wrong

| Symptom (measured text) | Cause | Fix |
|---|---|---|
| `Bind for 0.0.0.0:18910 failed: port is already allocated` | another container, or another program, already has that laptop port | `docker ps`, then `docker rm -f <name>`; or choose another host port (`API_PORT=18911 make up`). The failed `docker run` leaves a `Created` container holding the name: `docker rm` it too |
| `Conflict. The container name "/x" is already in use` | a container with that `--name` exists, maybe stopped | `docker rm -f x` |
| `[Errno 13] Permission denied` writing to a volume, `/ready` 503, `unhealthy` | the process is non-root and the mount point is owned by root. A new named volume copies the image's ownership only if the image has that folder | in the Dockerfile, `mkdir` the folder and `chown` it to your user before `USER` |
| Same on a **bind mount**, on Linux **(not run here)** | the laptop folder belongs to your uid, the container runs as 10001 | write to a named volume instead; on macOS, Docker Desktop mapped ownership and the write succeeded |
| Image far larger than expected | build tools, caches, the whole repo, or `chown -R` copied into a layer | `docker history IMAGE`; multi-stage; an allowlist ignore file; `--mount=type=cache` for uv's cache |
| `failed to connect to the docker API at unix:///...` (Docker 29) or `Cannot connect to the Docker daemon` (older) | the engine is not running, or `DOCKER_HOST` points somewhere wrong | start Docker Desktop; `unset DOCKER_HOST`; inside the course container, `make check` |
| `docker ps` stuck at `health: starting`, then `unhealthy`; `make up` ends `container ... is unhealthy` (after 20.7 s) | the `HEALTHCHECK` command fails inside the image | `docker inspect --format '{{json .State.Health}}' NAME` shows its output. Common: `curl: not found` on slim; the app listening on `127.0.0.1`, not `0.0.0.0`; a wrong port; a data folder it cannot write |
| `Makefile:2: *** missing separator.  Stop.` | a recipe line indented with spaces | indent with a TAB. `cat -et Makefile` shows TABs as `^I` |
| `make: 'eval' is up to date.` and nothing ran | a file or folder named `eval` exists and the target is not `.PHONY` | `.PHONY: up test eval gate gate-break down` |
| `"/app.py": not found` during `COPY` | wrong build context, or the ignore file excludes it | check the last argument of `docker build` and the allowlist |
| `exec: "uvicorn": executable file not found in $PATH` | the venv's `bin` is not on `PATH` | `ENV PATH="/opt/venv/bin:$PATH"` in the runtime stage |
| `exec /app/venv/bin/uvicorn: no such file or directory` | the venv was moved: its scripts point at the builder's path | copy it to the same path it was built at |
| `mounts denied: The path ... is not shared from the host` | compose run from inside a container, with a bind mount | run that `make`/`compose` from a laptop terminal (section 8) |
| `cannot attach stdin to a TTY-enabled container because stdin is not a terminal` | `-it` with no terminal (CI, a script) | drop `-it` |
| `docker stop` takes seconds; exit code 137 | shell-form `CMD`: the shell ignores SIGTERM | exec form: `CMD ["uvicorn", ...]` |
| The gate passes a break you were sure it would catch | the break was undone (a `compose run` recreated the service), or no case is near what you broke | pass the same variables to every compose command; add a boundary case |
