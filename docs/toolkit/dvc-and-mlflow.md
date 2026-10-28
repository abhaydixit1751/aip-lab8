# DVC and MLflow: a working primer

**Who needs this:** everyone, from **Lab 8 onward**. Lab 8 puts data under DVC,
writes a pipeline stage and logs experiments to MLflow; Labs 9 and 11 add stages;
Lab 12's CI rebuilds the pipeline with `dvc pull` and `dvc repro`. No earlier
course taught either tool, so this page does, on a toy project.

> **The minimum**
> 1. Git stores code and small pointer files. DVC stores the data and model files, by content hash.
> 2. `dvc add FILE` puts a file under DVC; commit the `FILE.dvc` pointer it writes, never the file.
> 3. `dvc.yaml` declares a stage (command, deps, params, outs, metrics); `dvc repro` reruns it only if something it declares changed.
> 4. Order matters: `dvc repro`, then `git commit` (including `dvc.lock`), then `dvc push`.
> 5. MLflow is a lab notebook for runs you *tried*; DVC is the record of what you *ship*.

Every command and output below was run in the course container (DVC 3.67.1,
MLflow 3.16.1, git 2.47.3) in a throwaway folder under `/tmp`. Outputs are
trimmed, never edited. To follow along without touching your repo, open a shell
in the container (`make shell`) and work in a fresh `git init` folder under `/tmp`.

## 1 · The mental model

| | Lives in | Committed to git |
|---|---|---|
| Code, `params.yaml`, `dvc.yaml` | your working folder | yes, the files themselves |
| Data, model files | DVC's **cache** (`.dvc/cache`) and **remote** | no: only their md5, in a `.dvc` pointer or `dvc.lock` |
| What produced what | `dvc.lock` | yes: the md5 of every input and output of the last run |
| Small metrics (`metrics.json`) | your working folder | yes, so you can diff them between commits |
| Experiments you tried | MLflow's database (`mlflow.db`) | no |

**Content addressing:** DVC stores a file under the md5 of its bytes, so git
can carry *which* version while the cache and remote carry *the bytes*. **A stage
is a declaration:** you say what a command reads and writes, and DVC can tell
whether an output is stale without running anything. **`dvc.lock` is the
receipt:** the hash of everything that went in and came out of the last run.

## 2 · Data under DVC: `init`, `add`

`dvc init` prints `Initialized DVC repository.`, creates `.dvc/` (with `config`)
and `.dvcignore`, and stages them in git (`git status --short` shows
`A  .dvc/config` and friends); commit them. Its banner about anonymous usage
analytics is normal. Now a data file, 1,000 rows of `x,y`:

```console
$ dvc add data/scores.csv
$ cat data/scores.csv.dvc
outs:
- md5: 2cbb0d202c8b5e0eb6708d7b91a4bacc
  size: 9004
  hash: md5
  path: scores.csv
$ cat data/.gitignore
/scores.csv
$ find .dvc/cache -type f
.dvc/cache/files/md5/2c/bb0d202c8b5e0eb6708d7b91a4bacc
```

The bytes went into the cache under their md5; a pointer, `scores.csv.dvc`,
appeared beside the file; and `data/.gitignore` stops git committing the real
file. Commit the pointer and the `.gitignore`, never the data.

In Lab 8 there is no `data/claims/.gitignore`: the repo's root `.gitignore`
already ignores the parquet. That is expected.

## 3 · Remotes: `remote add -d`, `push`, `pull`

The cache is on your machine only. A **remote** is where `dvc push` copies cache
entries so that a clone can `dvc pull` them. In industry it is S3, GCS or Azure
Blob; in this course it is a folder.

```console
$ dvc remote add -d store /tmp/dvstore
Setting 'store' as a default remote.
$ cat .dvc/config
[core]
    remote = store
['remote "store"']
    url = /tmp/dvstore
$ dvc push
1 file pushed
```

**`-d` means default**: it writes `remote = store` under `[core]`, so plain
`dvc push` and `dvc pull` know where to go. Without `-d` you would have to type
`dvc push -r store` every time. The remote lives in `.dvc/config`, which is in
git, so **commit `.dvc/config`** after adding it.

A clean clone gets the pointers from git and the bytes from the remote (this
clone was made after section 4, so it also pulls the model):

```console
$ git clone -q /tmp/dv /tmp/dvclone && cd /tmp/dvclone     # data/ holds only scores.csv.dvc
$ dvc pull
A       data/scores.csv
A       out/model.txt
2 files fetched and 2 files added
```

`dvc pull data/scores.csv` fetches one target only. Lab 12's CI does that: it
pulls the raw data and rebuilds the model rather than trusting a pushed one.

### The per-laptop remote: read this before Lab 8 Part C

Lab 8 uses `dvc remote add -d teamstore /workspace/.dvcstore`. That folder is
**inside your repo on your laptop**, ignored by git. The URL in `.dvc/config` is
committed, so on a teammate's laptop the same URL points at **their own**
`.dvcstore`, which is empty. Nothing you `dvc push` ever reaches them. The same
is true of CI in Lab 12: the runner on the production laptop sees only that
laptop's store.

What a teammate sees when they `dvc pull` from their own, empty store (simulated
here by pointing a clone at an empty folder):

```console
$ dvc pull
WARNING: Some of the cache files do not exist neither locally nor on remote. Missing cache files:
...
ERROR: failed to pull data from the cloud - Checkout failed for following targets:
out/model.txt
data/scores.csv
```

This is why the labs are arranged the way they are: every teammate copies
`claims.parquet` from the course zip (so `dvc status` agrees on it), the clean
clone in Lab 8 C4 happens **on the same laptop** (so it shares the store), and a
teammate **rebuilds** with `dvc repro --force` instead of pulling. A real team
would use one shared bucket and none of this would arise.

## 4 · Pipelines: `dvc.yaml`, `dvc repro`, `dvc.lock`

The toy training script picks the threshold on `x` that maximises accuracy,
searching a grid whose size comes from `params.yaml`:

```python
# train.py
"""Fit a one-number 'model': the threshold on x that maximises accuracy."""
import json, pathlib, yaml
import pandas as pd

p = yaml.safe_load(open("params.yaml"))["train"]
df = pd.read_csv("data/scores.csv")
grid = [i / p["steps"] for i in range(p["steps"] + 1)]
best = max(grid, key=lambda t: ((df.x >= t) == df.y).mean())
pathlib.Path("out").mkdir(exist_ok=True)
pathlib.Path("out/model.txt").write_text(f"{best}\n")
acc = float(((df.x >= best) == df.y).mean())
json.dump({"threshold": best, "accuracy": round(acc, 4)}, open("out/metrics.json", "w"))
print(f"threshold={best} accuracy={acc:.4f}")
```

```yaml
# params.yaml
train:
  steps: 10
```

```yaml
# dvc.yaml
stages:
  train:
    cmd: python train.py
    deps:
      - data/scores.csv
      - train.py
    params:
      - train.steps          # one key from ./params.yaml
    outs:
      - out/model.txt
    metrics:
      - out/metrics.json:
          cache: false       # small; kept in git so it can be diffed
```

| Key | Means | If it changes |
|---|---|---|
| `cmd` | the command to run | stage reruns |
| `deps` | files the command reads, **including the script** | stage reruns |
| `params` | keys in a YAML file the command reads | stage reruns |
| `outs` | files it writes; cached by DVC, ignored by git | DVC restores or rebuilds them |
| `metrics` | small JSON it writes; `cache: false` keeps it in git | `dvc metrics diff` shows it |

`dvc stage add -n train -d data/scores.csv -d train.py -p train.steps -o out/model.txt -M out/metrics.json python train.py`
writes the same stage (`-M`: a metric with `cache: false`).

**A params file that is not `./params.yaml`** (Lab 8's is
`labs/lab08/params.yaml`) takes a trailing colon, meaning "every key in this
file": `- labs/lab08/params.yaml:`. Write every list **one item per line**
(block style). In flow style, `params: [conf/train.yaml:]` is read as a key
named `conf/train.yaml:` inside the default `params.yaml`:

```console
$ dvc repro
ERROR: failed to reproduce 'train': Parameters 'conf/train.yaml:' are missing from 'params.yaml'.
$ dvc repro -q; echo "exit=$?"
exit=255
```

`-q` hid the error completely. Never use it while debugging.

### Running it (`dvc dag` first draws the graph: `data/scores.csv.dvc` → `train`)

```console
$ dvc repro
'data/scores.csv.dvc' didn't change, skipping
Running stage 'train':
> python train.py
threshold=0.5 accuracy=0.8240
Generating lock file 'dvc.lock'
To track the changes with git, run:
	git add dvc.lock out/.gitignore
```

`dvc.lock` now holds the receipt (trimmed):

```yaml
    deps:
    - path: data/scores.csv
      md5: 2cbb0d202c8b5e0eb6708d7b91a4bacc
    params:
      params.yaml:
        train.steps: 10
    outs:
    - path: out/model.txt
      md5: b6cd923e3b9f001ab14bc69acc4568a8
```

`out/.gitignore` lists `/model.txt` only, because `cache: false` leaves the
metrics file to git. Commit everything: `git add -A && git commit`.

### Only what changed reruns

```console
$ dvc repro
Stage 'train' didn't change, skipping
Data and pipelines are up to date.
$ sed -i 's/steps: 10/steps: 100/' params.yaml
$ dvc status
train:
	changed deps:
		params.yaml:
			modified:           train.steps
$ dvc params diff
Path         Param        HEAD    workspace
params.yaml  train.steps  10      100
$ dvc repro
Running stage 'train':
> python train.py
threshold=0.48 accuracy=0.8280
Updating lock file 'dvc.lock'
$ dvc metrics diff
Path              Metric     HEAD    workspace    Change
out/metrics.json  accuracy   0.824   0.828        0.004
out/metrics.json  threshold  0.5     0.48         -0.02
```

Editing **only a comment** in `train.py` also makes the stage stale
(`modified: train.py`): DVC hashes bytes, not meaning. `dvc repro --force`
reruns even when nothing changed; Lab 8's clean clone uses it to prove the
committed inputs rebuild the committed outputs. Both diffs take a revision
(`dvc metrics diff HEAD~2`); `dvc metrics show` prints the current values.

### Repro, commit, push: in that order

Commit after `repro` but forget `dvc push` (or push *before* `repro`), and git
has the new `dvc.lock` while the remote lacks the new model. A clone then fails:

```console
$ dvc pull
1 file fetched and 1 file added
ERROR: failed to pull data from the cloud - Checkout failed for following targets:
out/model.txt
```

The data arrived; the model did not. `dvc push` from the original repo fixes it
(`1 file pushed`), and the clone's next `dvc pull` succeeds. `dvc status -c`
compares your cache with the remote: `Cache and remote 'store' are in sync.`

## 5 · MLflow: a record of what you tried

DVC answers "what exactly produced the model in this commit?"; MLflow answers
"what did we try this week, and how did each attempt do?". It stores **runs**
(parameters, metrics, files) grouped into **experiments**, in a database named by
the **tracking URI**.

```python
# log_runs.py
import json
import mlflow
import pandas as pd

mlflow.set_tracking_uri("sqlite:///mlflow.db")      # one file, next to you
mlflow.set_experiment("threshold-demo")              # created if missing

df = pd.read_csv("scores.csv")
for steps in (10, 100):
    with mlflow.start_run(run_name=f"grid-{steps}"):
        grid = [i / steps for i in range(steps + 1)]
        best = max(grid, key=lambda t: ((df.x >= t) == df.y).mean())
        acc = float(((df.x >= best) == df.y).mean())
        mlflow.log_param("steps", steps)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("threshold", best)
        with open("result.json", "w") as f:
            json.dump({"steps": steps, "threshold": best}, f)
        mlflow.log_artifact("result.json")
        print(f"grid-{steps}: threshold={best} accuracy={acc:.4f}")
```

```console
$ python log_runs.py
2026/10/13 18:01:39 INFO mlflow.store.db.utils: Creating initial MLflow database tables...
2026/10/13 18:01:39 INFO mlflow.tracking.fluent: Experiment with name 'threshold-demo' does not exist. Creating a new experiment.
grid-10: threshold=0.5 accuracy=0.8240
grid-100: threshold=0.48 accuracy=0.8280
```

| Call | Stores | Example |
|---|---|---|
| `log_param` / `log_params` | an input, as text | `steps`, `random_state` |
| `log_metric` / `log_metrics` | a number | `accuracy`, `holdout_auc` |
| `set_tag` | a label you can search by | Lab 8 tags the prediction fingerprint |
| `log_artifact` | a file, copied under `mlruns/` | `metrics.json`, a plot |

Parameters and metrics go into `mlflow.db`; artefact files into
`mlruns/<experiment id>/<run id>/artifacts/` (here `mlruns/1/b385…/artifacts/result.json`).

**Comparing two runs from code**, without the UI:

```python
import mlflow
mlflow.set_tracking_uri("sqlite:///mlflow.db")
runs = mlflow.search_runs(experiment_names=["threshold-demo"], order_by=["metrics.accuracy DESC"])
print(runs[["tags.mlflow.runName", "params.steps", "metrics.accuracy", "metrics.threshold"]].to_string(index=False))
```

```console
tags.mlflow.runName params.steps  metrics.accuracy  metrics.threshold
           grid-100          100             0.828               0.48
            grid-10           10             0.824               0.50
```

### The UI

`mlflow ui --backend-store-uri sqlite:///mlflow.db --port <port>` serves the same
database in a browser. In the course, **`make mlflow`** on your laptop runs
exactly that inside the container, from `/workspace`, on port **18500**, and
Lab 8's `train.py` logs to `/workspace/mlflow.db`, so open
<http://localhost:18500> (not run here; the same command on another port was).
Click the experiment, tick two runs, press **Compare** to see their parameters
and metrics side by side. Ctrl-C stops the UI.

**The tracking URI is relative.** `sqlite:///mlflow.db` (three slashes) means
"`mlflow.db` in the current folder". MLflow 3.16 uses that same default if you
set nothing. Run your script from another folder and it silently creates a
**new, empty** database there; the UI then shows only the `Default` experiment.
Lab 8's `train.py` avoids this by building an absolute path from the repo root.

### DVC or MLflow?

| Question | Tool |
|---|---|
| Which data, code and params produced the model in this commit? | DVC (`dvc.lock`) |
| Can a clean clone rebuild it? | DVC (`dvc pull`, `dvc repro --force`) |
| Did this change move the metric, commit to commit? | DVC (`dvc metrics diff`) |
| What did we try this afternoon, and which was best? Side by side? | MLflow, and its UI |
| What gets shipped, rebuilt by CI? | DVC; MLflow is not in git and CI never sees it |

Do not let them overlap. Lab 8's DVC stage runs `train.py --no-mlflow`, so
rebuilding the pipeline does not add a run to the experiment log.

## 6 · Cheat sheet

| Command | What it does |
|---|---|
| `dvc init` | create `.dvc/` and `.dvcignore`; commit them |
| `dvc add FILE` | hash FILE into the cache; write `FILE.dvc` and a `.gitignore` entry |
| `dvc remote add -d NAME URL` | add a remote and make it the default; commit `.dvc/config` |
| `dvc push` / `dvc pull [TARGET]` | copy cache entries to / from the remote |
| `dvc stage add …` / `dvc dag` | write a stage into `dvc.yaml` / draw the pipeline |
| `dvc status` | what is stale, and why; `-c` compares cache with remote |
| `dvc repro` / `dvc repro --force` | rerun stale stages / rerun everything |
| `dvc params diff [REV]` | params in the workspace vs HEAD (or REV) |
| `dvc metrics show` / `dvc metrics diff [REV]` | current metrics / change vs HEAD (or REV) |
| `dvc checkout` | restore cached outputs to match `dvc.lock` |
| `set_tracking_uri("sqlite:///mlflow.db")`, `set_experiment(NAME)`, `start_run()` | where runs go; group them; one run |
| `log_param`, `log_metric`, `set_tag`, `log_artifact` | record inputs, numbers, labels, files |
| `mlflow.search_runs(experiment_names=[…])` | runs as a pandas table |
| `make mlflow` → <http://localhost:18500> | the course's UI (on your laptop) |

**The order, every time:** `dvc repro` → `git add -A && git commit` → `dvc push`.

## Try it (10 minutes)

In the container, in `/tmp` (not in `/workspace`):

1. Make the toy project above: `git init`, `dvc init`, a small CSV, `dvc add` it,
   `dvc remote add -d store /tmp/dvstore`, commit, `dvc push`.
2. Write `train.py`, `params.yaml` and `dvc.yaml` from section 4. `dvc repro`,
   commit, push.
3. Run `dvc repro` again and confirm it skips. Change `steps`, then run
   `dvc status`, `dvc params diff`, `dvc repro`, `dvc metrics diff`.
4. Clone into `/tmp/clone`, `dvc pull`, `dvc repro --force`. Confirm that
   `dvc metrics diff` and `git status --short` print nothing.
5. Run `log_runs.py` from section 5 and print the comparison table. Then, in an
   empty folder, run `python -c "import mlflow; print(mlflow.search_experiments())"`:
   a new `mlflow.db` appears there, holding only the `Default` experiment.

## If it goes wrong

| Symptom | Cause and fix |
|---|---|
| `output 'data/x' is already tracked by SCM (e.g. Git)` | the file was committed to git first. `git rm -r --cached data/x`, commit, then `dvc add data/x` (measured: the second `dvc add` then succeeds) |
| `failed to pull data from the cloud - Checkout failed for following targets` | the remote lacks those hashes: someone committed without `dvc push`, or you are pulling from a per-laptop store that never received them. Push from the laptop that built them, or rebuild with `dvc repro` |
| `No remote provided and no default remote set.` | no `-d` remote in `.dvc/config`, or `.dvc/config` was never committed |
| `remote 'store' already exists` | you ran `remote add` twice. Add `-f`, or leave it |
| `Parameters '…:' are missing from 'params.yaml'` | flow-style `params: [...]`. Use one `- file.yaml:` per line |
| `dvc repro -q` prints nothing, exit code 255 | it failed and `-q` hid why. Rerun without `-q` |
| a stage reruns although "nothing changed" | a dep's bytes changed (even a comment), or a param key changed. `dvc status` says which |
| after a failed `dvc repro`, `dvc status` says outs `deleted` | measured after the flow-style error. Fix the error and rerun; `dvc checkout` restores cached outs, `git checkout FILE` a `cache: false` metrics file |
| `dvc metrics diff` shows everything as new | the metrics file was never committed to git |
| MLflow UI shows no runs | the UI and your script used different `mlflow.db` files (relative URI, different folder), or `make mlflow` is not running. Port 18500, not 5000 |
