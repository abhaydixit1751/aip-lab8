# The shell, as the runsheets use it

**Who needs it:** everyone, **before Lab 8**. Used in Labs 8–21: every
evidence file in `reports/` is made with `| tee`, and the runsheets use pipes,
variables, loops and waits without explaining them. This page does.

> **The minimum**
> ```bash
> python labs/lab08/rebuild.py | tee reports/lab08/rebuild.txt   # see it AND keep it (tee -a appends)
> cmd 2>&1 | tee log.txt              # 2>&1: error messages go into the log too
> OMP_NUM_THREADS=1 python ...        # a variable for this one command only
> git add -A && git commit -m "..."   # &&: the second runs only if the first succeeded
> make shell                          # unsure where you are? make check, first line
> ```

Every output below is real: bash 5.2.37 in the course container, zsh on a macOS
laptop where noted. Anything not run is marked **(not run here)**.

## 0 · Laptop or container?

| | Laptop | Course container |
|---|---|---|
| Get there | your terminal (the Ubuntu/WSL one on Windows) | `make shell` (= `docker compose exec dev bash`) or VS Code *Reopen in Container* |
| `uname -sm` (measured) | `Darwin arm64` | `Linux aarch64` (or `x86_64`) |
| You are | yourself | `student`, in `/workspace` = the repo folder |
| Run here | `git push`/`pull`, `make up`/`check`/`mlflow`, `unzip`, coding agents | Python, `dvc`, `pytest`, `docker`, `uv lock` |

`exit` (or Ctrl-D) leaves the container. `docker compose exec dev <command>`
runs one command there, as Lab 10's agents do. There is no shell in between,
so a variable prefix (§3) needs `env`, as Lab 10 writes it. Measured:
`docker compose exec dev MODEL_DIR=artifacts/bundle printenv MODEL_DIR` fails
with `exec: "MODEL_DIR=artifacts/bundle": stat ...: no such file or directory`;
`docker compose exec dev env MODEL_DIR=artifacts/bundle printenv MODEL_DIR`
prints `artifacts/bundle`.

## 1 · Pipes, `tee` and redirection

`a | b` feeds what `a` prints into `b`: `docker logs claims | tail -5`
(Lab 11 4.4) shows the last five lines. `tee` prints **and** writes a file;
`tee -a` appends instead of starting the file again, which is why Lab 8 B3 and
B4 use `tee -a reports/lab08/repro_checks.txt`. Measured: `echo "run 1" | tee
out.txt; echo "run 2" | tee -a out.txt` leaves both lines; a later plain `echo
"run 3" | tee out.txt` leaves only `run 3`. Likewise `>` writes a file,
replacing it, `>>` appends, and `>/dev/null` throws output away.

**Two output streams.** Programs print results on *stdout* and errors on
*stderr*; a pipe and `>` carry only stdout. `2>&1` sends stderr to the same
place; `2>/dev/null` discards it:

```
$ ls /nope | tee err1.log            # the error shows on screen ...
ls: cannot access '/nope': No such file or directory
$ wc -l < err1.log                   # ... but the log is empty
0
$ ls /nope 2>&1 | tee err2.log       # now it is in the log
$ ls /nope 2>/dev/null; echo $?      # silent; $? is the exit code: 2 (failed)
```

Lab 9 2.1: `time docker build ... 2>&1 | tee /tmp/naive.log | tail -3`.
`docker build` writes its progress on stderr (not run here), so without `2>&1`
the log stays empty; `tail -3` shows only the end on screen. Lab 11's
`docker rm -f claims 2>/dev/null` hides "No such container" on a first run.

## 2 · `time`

`time <command>` runs it and reports three numbers (Lab 9 2.1; Lab 12 D1
`time python labs/lab12/deploy.py rollback`):

```
$ time sleep 1
real	0m1.005s     # wall clock: what you report
user	0m0.001s     # CPU time in your program
sys	0m0.000s     # CPU time in the kernel on its behalf
```

`real` far above `user + sys`: it was waiting (network, disk, another container);
`user` above `real`: it used several cores. zsh on the Mac differs (§10).

## 3 · Variables: a prefix, or `export`

```
$ OMP_NUM_THREADS=1 python -c 'import os; print(os.environ.get("OMP_NUM_THREADS"))'
1
$ python -c 'import os; print(os.environ.get("OMP_NUM_THREADS"))'
None                                # the prefix lasted one command
$ export OMP_NUM_THREADS=1          # every later command in this shell sees it
$ X=5; python -c 'import os; print(os.environ.get("X"))'
None                                # without export, only the shell sees X
```

Lab 8 B3 (`OMP_NUM_THREADS=1 python labs/lab08/train.py ...`) prefixes: one run
differs, the next does not. Lab 13 1.1 (`export MODEL_DIR=artifacts/bundle ...`)
exports, as several commands need it. `unset` removes it; so does a new terminal.

## 4 · `$(...)` and quoting

`$(command)` is replaced by what the command prints: `echo "in $(pwd)"` gives
`in /workspace`. Lab 10 D1, `git diff "$(git log --format=%H -1 --grep='spec and red tests')"`,
diffs against the sha the inner command finds; if it finds none, git gets an
empty string (`fatal: ambiguous argument ''`). Test the inner command alone first.

**Quotes.** `'single'` is literal; `"double"` still expands `$`. Measured:
`echo 'single: $HOME'` prints `single: $HOME`, `echo "double: $HOME"` prints
`double: /home/student`. So JSON goes in single quotes, being full of double
ones (Lab 15 1.2: `-d '{"question":"What is the room rent limit on the Silver plan?"}'`),
and `bash -c '...'` (§7) is single-quoted so the inner shell, not yours, reads
the loop. Put double quotes round `$(...)` and variables that may hold spaces.

## 5 · `&&`, `;`, loops and long lines

`a && b` runs `b` only if `a` succeeded; `a ; b` runs `b` regardless.
Measured: `false && echo "not printed"; echo "exit=$?"` prints only `exit=1`.
Lab 8 C1 `git add -A && git commit -m ...`: no commit if `add` failed. Lab 9
2.3 `curl -s http://host.docker.internal:18001/ready; echo`: `echo` always runs,
ending the line the JSON reply did not.

A loop with one `tee` for all its output (Lab 9 3.1):
`for c in 1 8 32; do python labs/lab09/load.py --concurrency $c; done | tee reports/lab09/load.txt`.
A `\` at the very end of a line continues the command on the next (Lab 12 D3,
Lab 15 1.2); nothing, not even a space, may follow it.

## 6 · Background jobs: `&`, `kill %1`, `wait`

Lab 16 2.2 starts a server, tests it and stops it in one terminal:

```bash
PACK_LEDGER=/tmp/contract_$P.jsonl python labs/lab16/server.py --pack $P --http --port 18090 &
sleep 2
python labs/lab16/contract_test.py --pack $P --url http://127.0.0.1:18090/mcp | tee reports/lab16/contract_http.txt
kill %1
```

`&` runs it in the background and returns the prompt. `jobs` lists such jobs
(`[1]+  Running  python -m uvicorn ...`, measured); `%1` is job 1 *of this shell*;
`kill %1` stops it; `wait` blocks until they end. Another terminal has no `%1`
(`kill: %1: no such job`): a job that runs for hours (the Lab 12 runner) gets its own.

## 7 · Waiting: `sleep`, `until`, `timeout`

Lab 10 3.2 and Lab 11 4.4 wait for a container to become ready:

```bash
timeout 30 bash -c 'until curl -sf http://host.docker.internal:18001/ready; do sleep 0.5; done'; echo
```

Inside out: `curl -sf` succeeds only when `/ready` answers 2xx;
`until X; do sleep 0.5; done` retries every half second until it does;
`timeout 30` kills the lot after 30 s. Measured with nothing listening and
`timeout 3`: back after `real 0m3.004s`, exit code **124** ("gave up"); then read
`docker logs claims`. Without `timeout`, a dead service hangs the terminal.

## 8 · `curl`

`-s` is silent (no progress bar). The rest, measured against a small FastAPI app in the container:

| Flag | Meaning | Measured |
|---|---|---|
| `-f` | fail on HTTP 4xx/5xx: no body, exit code 22 | on a 422: prints nothing, exit 22 |
| `-H 'content-type: application/json'` | add a header | left out: 422 `Input should be a valid dictionary` |
| `-d '{...}'` | send this body (makes it a POST) | `{"you_asked":"What is the room rent limit ..."}` |
| `-m 600` | give up after 600 s (Lab 15) | not run |
| `-o /dev/null -w '%{http_code}\n'` | print only the status code | `422` |

Exit code 7: nothing listening. Inside the container use
`host.docker.internal`, not `localhost` (lab09/CONCEPTS "Where localhost is").

## 9 · Finding and filtering

```
$ grep -E "auc|n_iter|finger" artifacts/lab08/metrics.json     # Lab 11 3.2; -E: | means "or"
  "holdout_auc": 0.921802,
  "n_iter": 67,
  "prediction_fingerprint": "361ce589...",
$ seq 1 100 | head -3          # first lines (default 10); tail -2: the last two
$ du -sh data/claims artifacts # disk use, human-readable: 1.5M  data/claims
$ ls -lh artifacts/lab08       # sizes and dates
$ find data -name '*.parquet' -size +1M  # any depth, with a condition: data/claims/claims.parquet
```

Lab 9 2.1's `du -sh /app/* /app/.[!.]* 2>/dev/null` adds hidden files
(`.[!.]*`: a dot, then anything but a second dot).

**`awk`** splits each line on spaces into fields `$1`, `$2`, ... Lab 12 D3:
`docker logs aip2-prod-router 2>/dev/null | awk '$2 ~ /^(stable|baseline|canary)$/ && $3 != 200'`.
The router logs `$time_iso8601 $pool $status $request_time $request_uri`
(`log_format pools` in `labs/lab12/deploy.py`): `$2` is the pool, `$3` the
status. Measured on five such lines plus one nginx notice: `awk '{print $2}'`
printed the pools **and** `10:00:02` from the notice. The `$2 ~ /.../` condition
keeps request lines only, `$3 != 200` the failures
(`... baseline 502 0.000 /predict`). Per-pool counts:
`awk '$2 ~ /^(stable|baseline|canary)$/ {print $2}' | sort | uniq -c`.

## 10 · Windows (WSL) paths, and zsh on a Mac

In the Ubuntu terminal `~` is your **Linux** home, so `~/Downloads` is not where
Windows saves downloads (not run here). Windows' C: drive is `/mnt/c`:

```bash
ls /mnt/c/Users/                                   # find your Windows user name
unzip /mnt/c/Users/<you>/Downloads/AI-in-Practice-2-Week2.zip -d .
sudo apt install -y unzip                          # if unzip is missing
```

Unzip *from* `/mnt/c`, but keep the repo in the Linux home (START_HERE, Windows
notes). `explorer.exe .` opens the current folder in Windows Explorer.

The Mac's terminal runs zsh, not bash. Two differences, measured: `time` prints
one line (`( sleep 0.3; )  0.00s user 0.00s system 0% cpu 0.303 total`), and a
pattern matching no file is an error (`zsh: no matches found: /tmp/.[!.]*nomatch`):
quote it, or run the command in the container. The container has no `unzip`.

## Try it (10 minutes)

In the container (`make shell`). Predict each output before you press Enter.

```bash
cd /tmp && rm -rf shtry && mkdir shtry && cd shtry
for n in 1 2 3; do echo "run $n at $(date +%T)"; sleep 1; done | tee runs.txt
ls /nope 2>&1 | tee -a runs.txt
time OMP_NUM_THREADS=1 python -c 'import os; print("inside:", os.environ["OMP_NUM_THREADS"])'
python -c 'import os; print("after:", os.environ.get("OMP_NUM_THREADS"))'
python -m http.server 18997 >/dev/null 2>&1 &
timeout 10 bash -c 'until curl -sf http://localhost:18997/ >/dev/null; do sleep 0.5; done' && echo "server up"
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:18997/runs.txt
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:18997/nothing-here
kill %1; wait
grep -E "run (1|3)" runs.txt | awk '{print $2, $4}'
du -sh /workspace/data/claims; find /workspace/labs -name 'RUNSHEET.md' | wc -l
```

Then: how many lines are in `runs.txt`, and why is the `ls` error among them? Rerun
that line with `tee` instead of `tee -a`: what is left? Why does `after:` print `None`?

## If it goes wrong

| You see | Meaning and fix |
|---|---|
| `dvc: command not found`, `ModuleNotFoundError` | You are on the laptop: `make shell` |
| `make: command not found` | PowerShell on Windows (use the Ubuntu terminal), or make not installed |
| `exec: "VAR=...": ... no such file or directory` | Prefix through `docker compose exec`: add `env` (§0) |
| A report file holds only the last run | `tee` or `>` where you needed `tee -a` or `>>` |
| Errors on screen, missing from the log | Add `2>&1` before the pipe |
| Python does not see your variable | `export` it, or prefix the command (§3) |
| A wait loop never ends | Wrap it: `timeout 30 bash -c '...'` (§7) |
| `timeout` exits with 124 | The service never became ready: `docker logs <name>` |
| `curl` exit 7, "Failed to connect" | Nothing listening; in the container use `host.docker.internal` |
| `curl -sf` prints nothing, exit 22 | An HTTP error: rerun without `-f` to see the body |
| `fatal: ambiguous argument ''` | An empty `$(...)`: test the inner command alone |
| `zsh: no matches found` | zsh on the Mac: quote the argument, or use the container |
| `unzip: cannot find or open ~/Downloads/...` on WSL | Use `/mnt/c/Users/<you>/Downloads/...` (§10) |
