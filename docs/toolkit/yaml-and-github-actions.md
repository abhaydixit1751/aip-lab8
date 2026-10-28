# Toolkit — YAML, GitHub Actions, and enough PromQL

**Who needs this.** Lab 8 (`params.yaml`, `dvc.yaml`), Lab 11 (a DVC stage),
Lab 12 (`gate.yaml`, `.github/workflows/ci.yml`), Lab 13 (`monitor_gate.yaml`;
PromQL if you run `observe.py up --no-grafana`), Lab 16 (`contracts/<pack>.yaml`)
and the capstone (`ci.yml`, `compose.yaml`).

**Measured with** PyYAML 6.0.3 and ruamel.yaml 0.19.1 (DVC 3.67.1's parser) in
the course container: every YAML snippet here was parsed. Actions examples are
**(syntax checked, not run on GitHub)**. The PromQL is copied from
`labs/lab13/dashboard.json` and was not run here.

> **The minimum.**
> - Three shapes: `key: value` (a mapping), `- item` (a list), plain values
>   (scalars). Indent with **spaces**, never tabs.
> - A `: ` inside an unquoted value breaks the file. Quote it: `name: "Step 2: train"`.
> - In any file DVC reads, write lists in **block style** (one `- item` per line).
> - Check every file before you push:
>   `python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <file> && echo ok`
> - A workflow is jobs, a job is steps, `needs:` orders jobs, and a step fails
>   when its command exits non-zero.

---

## 1 · YAML

### Three shapes

```yaml
# A mapping: key, colon, space, value.
server:
  host: 0.0.0.0
  port: 18001
  debug: false
  log_file: null
# A list: one item per line, each starting with "- ".
languages:
  - en
  - hi-en
# A list of mappings: each "- " starts a new item.
checks:
  - name: latency
    max_ms: 50
  - name: errors
    max_ratio: 0.001
```

`yaml.safe_load` gives `{'server': {'host': '0.0.0.0', 'port': 18001, ...},
'languages': ['en', 'hi-en'], ...}`. Indentation is the structure.

### Scalars: what you type is not always what you get

YAML guesses the type of an unquoted value. Two parsers, same file (measured):

| You write | PyYAML (`yaml.safe_load`) | ruamel.yaml (DVC) | Lesson |
|---|---|---|---|
| `python: 3.10` | `3.1` (a float) | `3.1` | quote versions: `"3.10"` |
| `country: NO` | `False` | `'NO'` | quote yes/no/on/off words |
| `start: 12:30` | `750` (base 60) | `'12:30'` | quote times |
| `id: 0123` | `83` (octal) | `123` | quote IDs with leading zeros |
| `on: push` | key `True` | key `'on'` | see `on:` in §2 |
| `empty:` or `tilde: ~` | `None` | `None` | both mean null |

PyYAML follows YAML 1.1, ruamel.yaml YAML 1.2. If a string could look like
anything else, **quote it** (single quotes literal, double quotes allow `\n`).

### The colon trap

Both of these fail with `mapping values are not allowed here` (measured):

```
steps:
  - name: Step 2: train          # line 2, column 17
    run: python train.py
  - name: Report
    run: echo "status: ok"       # the quotes do not start the value, so they do not protect it
```

Quote the **whole** value, or use a `|` block:

```yaml
steps:
  - name: "Step 2: train"
    run: python train.py
  - name: Report
    run: 'echo "status: ok"'
```

### Block style, flow style, and the DVC trap

Flow style is the JSON-like form, `[a, b]` and `{k: v}`. Legal YAML, but in Lab 8
it changes the meaning (measured):

```yaml
block:
  params:
    - labs/lab08/params.yaml:
flow:
  params: [labs/lab08/params.yaml:]
```

| | PyYAML | ruamel.yaml (what DVC uses) |
|---|---|---|
| `block` | `[{'labs/lab08/params.yaml': None}]` | `[{'labs/lab08/params.yaml': None}]` |
| `flow` | `[{'labs/lab08/params.yaml': None}]` | `['labs/lab08/params.yaml:']`, a string ending in a colon |

The parse check passes on both, and DVC then looks for a parameter *named*
`labs/lab08/params.yaml:`. **A file that parses can still mean the wrong thing.**
(In DVC's `params:` list, `- labs/lab08/params.yaml:` with its trailing colon
means "every parameter in this file".)

### Multi-line strings, comments, tabs

```yaml
literal: |
  echo one
  echo two
folded: >
  This long sentence
  becomes one line.
```

gives `'echo one\necho two\n'` and `'This long sentence becomes one line.\n'`
(`|-` drops the last newline). Use `|` for shell commands: lines stay lines, and
colons and quotes inside need no escaping.

`#` after a space starts a comment (`run: echo hello #world` gives
`'echo hello'`); without the space it is text (`http://x/#anchor` survives). A
tab in the indentation is an error: `found character '\t' that cannot start any
token`. Set your editor to insert spaces in `.yml` and `.yaml` files.

### Check before you push

```bash
python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" labs/lab12/ci.template.yml && echo "yaml ok"
```

A broken file prints a traceback ending in a line and column: look there and
at the line above. It proves the file is YAML, not that it means what you meant.

---

## 2 · GitHub Actions

A **workflow** is one file in `.github/workflows/`, run when an event in `on:`
happens. It holds **jobs**, which run in parallel unless `needs:` orders them;
each job is a list of **steps** (`run:` a command, or `uses:` a packaged action)
on one **runner**. Yours is `labs/lab12/runner.sh`, in the production laptop's
course container.

### An annotated example

A generic pipeline: build a documentation site, check it, publish it from `main`
only. It uses every construct the Lab 12 template asks you to look up, and none
of Lab 12's jobs. **(syntax checked, not run on GitHub)**

```yaml
name: docs

on:
  push:
    branches: [main]          # a push to main
  pull_request:               # any pull request
  workflow_dispatch:          # the "Run workflow" button

env:                          # every job, every step
  SITE_DIR: build/site

jobs:
  check:
    runs-on: [self-hosted, aip2]      # a runner with ALL these labels
    steps:
      - uses: actions/checkout@v7     # a fresh copy of the commit
      - name: "Build and check: internal links only"   # quoted: contains ": "
        run: |
          python tools/build_site.py --out "$SITE_DIR"
          python tools/check_links.py "$SITE_DIR"

  publish:
    needs: check                               # only if check succeeded
    if: github.ref == 'refs/heads/main'        # skipped on pull requests
    runs-on: [self-hosted, aip2]
    concurrency:                               # one publish at a time, repo-wide
      group: publish-site
      cancel-in-progress: false
    env:                                       # this job only
      ARCHIVE: site-${{ github.sha }}.tar.gz
    steps:
      - uses: actions/checkout@v7
      - name: Archive this commit's site
        run: |
          SHORT=${GITHUB_SHA::12}
          python tools/build_site.py --out "$SITE_DIR"
          echo "commit $GITHUB_SHA, short $SHORT, archive $ARCHIVE"
          tar czf "/srv/site-$SHORT.tar.gz" "$SITE_DIR"
```

Print any workflow's `needs` graph (on the template: `{'lint': None, 'test': 'lint'}`):

```bash
python -c "import yaml,sys; print({j: v.get('needs') for j, v in yaml.safe_load(open(sys.argv[1]))['jobs'].items()})" labs/lab12/ci.template.yml
```

### Key by key

- **`on:`** lists the events. PyYAML reads the key as `True` (GitHub reads
  `on`), so only a script doing `d["on"]` breaks.
- **`runs-on:`** picks a runner with every listed label. Ask for a label no
  runner has, and the job waits in *Queued* forever.
- **`needs:`** takes a job or a list (`needs: [a, b]`). Naming a job that does
  not exist is a workflow error. If a needed job fails or is **skipped**, this
  job is skipped too.
- **A step fails when its command exits non-zero.** That is the whole mechanism
  behind every gate in this course: `gate.py` exits 1, the step fails, the job
  fails, and the jobs that need it never start.
- **Pipes hide failures** without `pipefail` (measured: `bash -e -c "false |
  tee /dev/null; echo ..."` carries on; with `-eo pipefail` it exits 1). GitHub
  documents `run:`'s default on Linux as `bash -e {0}` and `shell: bash` as
  `bash --noprofile --norc -eo pipefail {0}`: a step that pipes needs `shell: bash`.
- **`env:`** exists at workflow, job and step level (innermost wins); `run:`
  reads it as `$SITE_DIR`. **`${{ ... }}`** is a GitHub expression, replaced by
  text **before** the shell starts; `$GITHUB_SHA` is an environment variable the
  shell reads **while** it runs. Both hold the 40-character commit hash.
- **`${GITHUB_SHA::12}`** is bash, not GitHub: the first 12 characters
  (`3f2a9c4e8b1d7f60...` → `3f2a9c4e8b1d`, measured).
- **`if:`** is already an expression, so `${{ }}` is optional there. `github.ref`
  is `refs/heads/main` for a push to main, `refs/pull/<n>/merge` for a pull
  request, and the chosen branch for *Run workflow*. Also useful:
  `github.event_name` (`push`, `pull_request`, `workflow_dispatch`).
- **`concurrency:`** at the top of a workflow (the template's `group:
  ci-${{ github.ref }}`) allows one run per branch at a time; on a **job**, with a
  fixed group name, one such job at a time across all branches and runs. GitHub
  documents at most one running and one pending per group, a newer pending one
  replacing the older. `cancel-in-progress: true` would stop a deploy half-way.

### Passing files between jobs

`actions/checkout` cleans the working directory, so a file one job made is not
there for the next: that is why `publish` above builds the site again. GitHub's
usual answer is an **artefact**: a step `uses: actions/upload-artifact` (with a
`name:` and a `path:`) in one job, and `uses: actions/download-artifact` with the
same `name:` in a job that `needs` it. The course does not use them. All your jobs run on one runner that already sees
the laptop's DVC store, so one job runs `dvc push` and the next `dvc pull`: the
files never leave the laptop, and DVC checks them by hash. An artefact would
send the model to GitHub's storage and back to the same laptop.

### What the Lab 12 template asks you to look up

| Template comment | Where above |
|---|---|
| "needs lint", "change to `reproduce`" | `needs:` |
| "ONLY on a push to main (look up `if:` and github.ref)" | `if:` and the `github.ref` values |
| "tag it $IMAGE:<first 12 characters of $GITHUB_SHA>" | `${GITHUB_SHA::12}`; `${{ }}` vs `$VAR` |
| "Only one deploy at a time, ever, across branches" | `concurrency:` on a job |
| "on the very first run nothing has started it yet" | not syntax: a design decision, yours |

---

## 3 · PromQL, for `observe.py up --no-grafana`

Without Grafana, type the dashboard's queries into Prometheus:
<http://localhost:18090> → **Query**. The service pushes metrics every 5 s
(`telemetry.py`, `export_interval_millis=5000`).

| In your code (OpenTelemetry) | Type | In Prometheus |
|---|---|---|
| FastAPI instrumentation's request duration | histogram (ms) | `http_server_duration_milliseconds_bucket`, `_count`, `_sum` |
| `create_counter("claims_decisions")` | counter | `claims_decisions_total` |
| `create_histogram("claims_p_reject")` | histogram | `claims_p_reject_bucket`, `_count`, `_sum` |

A **counter** only goes up, so its raw value (decisions since the container
started) is rarely what you want. A **histogram** is a set of counters, one per
bucket: `_bucket{le="50"}` counts observations ≤ 50, cumulatively; `_count` is
the number of observations and `_sum` their total.

| Piece | Example | Means |
|---|---|---|
| selector | `claims_decisions_total{language="hi-en"}` | the series with that label value |
| regex matcher | `{http_status_code=~"5.."}` | any 5xx code |
| `rate(x[w])` | `rate(claims_decisions_total[30s])` | per-second increase of a counter over window `w` |
| `increase(x[w])` | `increase(claims_decisions_total[5m])` | total increase over `w` (about rate × w) |
| `sum by (l) (...)` | `sum by (language) (...)` | add series, keeping one per value of `l`; plain `sum` keeps one |
| `histogram_quantile(q, ...)` | `histogram_quantile(0.95, ...)` | the q-th quantile, interpolated within a bucket |
| `or vector(0)` | | 0 instead of "no data" when the left side is empty |

`rate()` needs two samples in its window; at a 5 s export interval `[30s]` holds
about six. Much shorter, and the panel goes blank.

### The dashboard's queries, explained

```
histogram_quantile(0.95, sum by (le) (rate(http_server_duration_milliseconds_bucket{http_target="/predict"}[5m])))
```

Inside out: the per-second rate of each `/predict` latency bucket over five
minutes; summed across containers and every other label **except `le`** (the
bucket edge, which `histogram_quantile` needs); then the bucket where 95% of
requests fall, interpolated. That is the p95 SLO panel. The time-series panel
uses 0.5, 0.95 and 0.99 over `[30s]`.

```
sum(rate(http_server_duration_milliseconds_count{http_status_code=~"5.."}[5m]))
  / sum(rate(http_server_duration_milliseconds_count[5m])) or vector(0)
```

5xx requests per second over all requests per second: the error ratio. With no
5xx series at all the division is empty, and `or vector(0)` shows 0.

```
sum(increase(claims_decisions_total[5m]))                                  # claims decided, last 5 min
sum by (instance) (rate(http_server_duration_milliseconds_count[30s]))    # requests/s per container
sum by (channel) (rate(claims_decisions_total[30s]))                       # claims/s per channel
histogram_quantile(0.5, sum by (le) (rate(claims_p_reject_bucket[30s])))  # median model score
sum by (language) (rate(claims_decisions_total{decision="auto_approve"}[30s]))
  / sum by (language) (rate(claims_decisions_total[30s]))
```

The last is the auto-approval rate per language: both sides keep the `language`
label, so they divide series by series (the four-fifths panel divides `hi-en` by
`en` the same way). The score quantiles are only as precise as your bucket edges:
with the defaults (0 to 10,000) every score lands in the first bucket, which is
why Lab 13 asks you to choose buckets around your threshold.

---

## Try it

1. In the course container, copy a block from §1 into `/tmp/t.yaml`, run the
   check, then add `: x` to a value and run it again. Read the line and column.
2. Run the `needs` one-liner on your `.github/workflows/ci.yml`. Is the graph
   `lint → reproduce → test → eval-gate → image → deploy`?
3. In Lab 13, with traffic flowing, type into Prometheus in turn:
   `claims_decisions_total`, then `rate(claims_decisions_total[30s])`, then
   `sum by (language) (rate(claims_decisions_total[30s]))`. Watch a counter
   become a rate, then one line per language.

## If it goes wrong

| Symptom | Cause and fix |
|---|---|
| GitHub: failed run, no jobs, "workflow file issue" | Not valid YAML: run the check. Often `: ` in an unquoted name or `run:` |
| `mapping values are not allowed here` | An unquoted `: ` at that line and column. Quote the value, or use `run: \|` |
| `found character '\t'` | A tab in the indentation. Use spaces |
| The check passes, DVC says `Parameters ... are missing` | Flow style in `dvc.yaml`. Rewrite the list in block style |
| A version or ID changed (`3.10` → `3.1`, `0123` → `83`) | An unquoted scalar read as a number. Quote it |
| Job waits in *Queued* | Runner not running, or `runs-on` asks for a label it lacks |
| "job depends on unknown job" | `needs:` names a job that does not exist (yet) |
| A job you expected was skipped | Its `if:` was false, or a job it `needs` was skipped or failed |
| A step passed although the test inside it failed | A pipe without `pipefail`: add `shell: bash` |
| Prometheus or Grafana: "No data" | Query the bare metric name first; a counter ends `_total`, a histogram `_bucket` |
