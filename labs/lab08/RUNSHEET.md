# Lab 8 — Runsheet

**Follow this top to bottom.** Every step says *why* it exists, *what* to do,
*how* to do it, and how you know you are finished.

| | |
|---|---|
| [`OVERVIEW.md`](OVERVIEW.md) | **why**: read before the lab |
| [`README.md`](README.md) | **the brief**: targets, deliverables, rubric |
| [`CONCEPTS.md`](CONCEPTS.md) | **the reference**: concept → code → theory. Keep it open |
| [`CODE_GUIDE.md`](CODE_GUIDE.md) | **the code**: what is provided, what is yours |
| this file | **the actions**: follow it during the lab |

**Every command runs inside the course container** (VS Code *Reopen in
Container*, or `make shell`), in `/workspace`, unless it says *on your laptop*.
The exceptions are `git push` / `git pull`: run those wherever your GitHub
login lives, usually your laptop's terminal.

**Three roles, rotated at every part.** *Driver* types. *Navigator* reads this
runsheet aloud and says what comes next. *Skeptic* reads every number aloud,
asks "compared to what?", and keeps the notes, which become your report.

---

## The lab in one line

> The handover says AUC 0.997 and "please deploy". Find out whether it
> rebuilds, whether it is honest, and what it is worth, and make all three
> answers reproducible by someone who is not you.

---

## Before you sit down

- [ ] `START_HERE_LAB8.md` done: team repo on GitHub, **all three** teammates
      cloned it, data copied in, `make check` clean on each laptop
- [ ] `git config --global user.name` is set **inside** the container
      (`make check` warns if not)
- [ ] `OVERVIEW.md` read
- [ ] T5 §1–§5 skimmed

> ⚠️ **The one that will bite you.** Only one laptop's work ends up in the
> team repo per part. Decide whose laptop drives each part *now*, and make
> sure the other two have `git pull`ed before Part C5.

---

# 0 · Setup — 10 min

**0.1** Confirm you are inside the container, then make a folder for evidence:

```bash
make check                      # on your laptop, OR: python scripts/check_env.py inside
mkdir -p reports/lab08
```

**0.2** Assign roles for Part A. Write them at the top of your notes.

> **Done when:** `Environment ready.` and three names beside three roles.

---

# 1 · Part A — the handover — 30 min

**Why.** You cannot fix what you have not measured, and a team that starts by
editing code will never know which change mattered.

**1.1 — `A1`. The inventory.** Open all four files in `supplied_model/`. Make
a four-row table in your notes: **code · data · weights · environment**. For
each: what is pinned exactly, what loosely, what not at all.

> 💡 **Theory.** T5 §1: the artefact problem.

**1.2 — `A2`. Rebuild it.**

```bash
python labs/lab08/rebuild.py | tee reports/lab08/rebuild.txt
```

About 15 seconds. Read the pairwise table: how many claims change decision
between builds of the *same* script, and how many customers a day is that?

Then answer: why does `n_iter` change between runs? Open the scikit-learn
docs for `HistGradientBoostingClassifier` and read `early_stopping`,
`validation_fraction` and `random_state`.

> Note the row **shipped vs run *n***. Nobody can rebuild the pickle you were
> handed, not even with the script that made it.

**1.3 — `A3`. The leak.** Write `importance()` in `inspect_supplied.py`
(CODE_GUIDE §3, CONCEPTS "Permutation importance"). Then:

```bash
python labs/lab08/inspect_supplied.py | tee reports/lab08/leak.txt
```

One feature will dominate. Make the timing argument in one sentence: **who
writes this value, and when, relative to the decision?** Then check what the
model card said about it.

> 💡 **Theory.** T5 §4: what the model may know.

**1.4 — `A4`.** `leak.txt` prints what "approve everything" scores. Compare it
with the card's 0.981. Note it down.

> **Done when:** four-row inventory, rebuild table, one named leak with its
> timing argument, and the approve-everything baseline are in your notes.

---

# 2 · Part B — reproducible training — 50 min

**Why.** "It's the same model" needs to be a yes/no answer with a tool that
gives it. After this part, yours is.

**2.1 — `B1`. `params.yaml`.** Make it the single home of everything that can
change the model. At minimum: add a `random_state` under `model:`, and remove
the leak from `features:` with a comment saying why. Change `run_name`.

**2.2 — `B2`. `train.py`.** Write the three functions below the `YOURS` banner
(CODE_GUIDE §2). Then train twice and compare:

```bash
python labs/lab08/train.py --out /tmp/run1 --no-mlflow
python labs/lab08/train.py --out /tmp/run2 --no-mlflow
python labs/lab08/check_reproducible.py /tmp/run1 /tmp/run2 | tee reports/lab08/repro_checks.txt
```

> **Checkpoint.** `BIT-IDENTICAL`. The reference takes about 4 seconds to
> train and lands at holdout AUC 0.9218. Yours may differ in the third decimal
> place if your configuration differs; that is fine.

> ⚠️ **If it says `CANNOT COMPARE`, read the reason.** It refuses a missing file,
> an empty fingerprint, and a `metrics.json` that does not match the
> predictions beside it. Do not "fix" the checker: it exists because the first
> version passed on two empty fingerprints.

**2.3 — `B3`. Threads.**

```bash
OMP_NUM_THREADS=1 python labs/lab08/train.py --out /tmp/run1t --no-mlflow
python labs/lab08/check_reproducible.py /tmp/run1 /tmp/run1t | tee -a reports/lab08/repro_checks.txt
```

**2.4 — `B4`. Row order.** Same rows, different order:

```bash
python -c "import pandas as pd; pd.read_parquet('data/claims/claims.parquet').sample(frac=1, random_state=7).to_parquet('/tmp/shuffled.parquet', index=False)"
python labs/lab08/train.py --data /tmp/shuffled.parquet --out /tmp/shuf --no-mlflow
python labs/lab08/check_reproducible.py /tmp/run1 /tmp/shuf --threshold 0.5 --threshold 0.018 | tee -a reports/lab08/repro_checks.txt
```

(0.018 is the reference solution's operating threshold from Part D. Rerun
with yours once you have it.)

Now measure it the other way: temporarily remove your row-order fix from
`load_data()` (keep the seed), rerun those two `train.py` lines into
`/tmp/run1_noorder` and `/tmp/shuf_noorder`, compare *them*, then **put the fix
back.** Report both.

> The reference measured this: with the seed alone, a shuffled file changes
> **6,554 of the 45,365** decisions at the operating threshold. A seed is necessary.
> It is not sufficient.

**2.5 — `B5`. Category order.** Temporarily make `prep()` use
`X[c].astype("category")` the way the supplied script did, train into
`/tmp/cat_inferred`, and compare with `/tmp/run1`. Report what you find. Then
decide which version to keep, and say why.

**2.6 — `B6`.** From `/tmp/run1/metrics.json`: holdout AUC and accuracy at
0.5. Put them beside the supplied model's (from `leak.txt`) and beside
"approve everything".

> **Done when:** `repro_checks.txt` shows BIT-IDENTICAL for runs, threads and
> row order, and your notes have the seed-only row-order result and the
> category-order result.

---

# 3 · Part C — version all four parts — 40 min

**Why.** A reproducible script on one laptop is not yet a reproducible
*system*. The test is whether a stranger with a clean clone gets your model.

**3.1 — `C1`. Data into DVC.**

```bash
dvc init
dvc add data/claims/claims.parquet
dvc remote add -d teamstore /workspace/.dvcstore
git add -A && git commit -m "Lab 8: claims data under DVC"
```

The `.dvcstore` folder is a **stand-in remote** on your laptop (git ignores
it). In industry it is S3, GCS or Azure Blob. The commands do not change.
`-d` makes it the default remote, so `dvc push` and `dvc pull` need no name.
Because it is a folder on **this** laptop, your teammates cannot `dvc pull`
from it: each of them copies the data from the zip and rebuilds (C5). Lab 12
turns that limitation into a design decision. New to DVC:
[`docs/toolkit/dvc-and-mlflow.md`](../../docs/toolkit/dvc-and-mlflow.md).

> DVC does not write a `data/claims/.gitignore`, because the repo's root
> `.gitignore` already covers the file. That is expected.

**3.2 — `C2`. The pipeline.** Create `dvc.yaml` at the repo root with one
stage, `train` (CONCEPTS "A DVC stage"). The command it runs is
`python labs/lab08/train.py --params labs/lab08/params.yaml --out artifacts/lab08 --no-mlflow`.

```bash
dvc repro                        # NOT dvc repro -q -- see below
git add -A && git commit -m "Lab 8: training pipeline"
dvc push
```

**In that order**: repro, commit, push. Pushing before `repro` leaves the
model out of the remote, and the clean clone fails later.

> ⚠️ **Block style, not flow style, in `dvc.yaml`.** `params: [labs/lab08/params.yaml:]`
> is read as the *default* `params.yaml`. The reference stage silently never
> ran, and `-q` hid the error. Write the list one item per line, and never
> use `-q` while debugging.

> **Checkpoint.** `git ls-files | grep -E "dvc.lock|metrics.json|claims.parquet.dvc"`
> prints three files. `git ls-files | grep parquet$` prints **nothing**.

**3.3 — `C3`. MLflow.** Log two runs: the params as handed over
(`params.supplied.yaml`, a frozen copy of the starting file: leak in, no seed),
and yours.

```bash
python labs/lab08/train.py --params labs/lab08/params.supplied.yaml --out /tmp/mlf_supplied
python labs/lab08/train.py --out /tmp/mlf_honest
```

Then **on your laptop**: `make mlflow` and open <http://localhost:18500>.
Select both runs → *Compare*. Screenshot → `reports/lab08/mlflow.png`. Ctrl-C
stops the UI.

> If `params.supplied.yaml` crashes `build_model()` because there is no
> `random_state`, your code is telling you something. Decide whether a missing
> seed should be an error or a default, copy the file to `/tmp` and add a seed
> if you need the run, and say which you chose. Do not edit the frozen copy.

**3.4 — `C4`. The clean clone.** The strongest test you have: a fresh copy
that knows nothing except what is committed.

```bash
rm -rf /tmp/clone && git clone /workspace /tmp/clone && cd /tmp/clone
dvc pull
dvc repro --force
dvc metrics diff                 # expect: no output
git status --short               # expect: no output
python labs/lab08/check_reproducible.py /workspace/artifacts/lab08 /tmp/clone/artifacts/lab08 | tee /workspace/reports/lab08/clean_clone.txt
cd /workspace
```

> **Checkpoint.** `BIT-IDENTICAL`. The reference takes about 5 seconds from
> clone to verdict.

**3.5 — `C5`. A teammate's laptop.** Driver pushes (**on your laptop**:
`git push`). On a second teammate's laptop, **on the laptop**: `git pull`.
Then inside their container:

```bash
dvc status                       # data/claims/claims.parquet must NOT say "modified"
dvc repro --force
dvc metrics diff | tee reports/lab08/teammate.txt
```

If `prediction_fingerprint` does **not** appear in the diff, the teammate's
model is bit-identical to the committed one. If `environment.machine` appears,
the two laptops have different CPUs (e.g. `aarch64` vs `x86_64`). That makes
it a stronger result, not a failure. Say so in the report.

> **Done when:** `clean_clone.txt` says BIT-IDENTICAL and `teammate.txt` has
> no fingerprint row.

---

# 4 · Part D — the operating point — 35 min

**Why.** A model that predicts well is still useless until someone picks a
threshold, and the threshold decides what the model costs. Price the errors.

**4.1 — `D1`.** Write `cost_at()` and `choose_thresholds()` in
`operating_point.py` (CONCEPTS "The operating point"). Then:

```bash
python labs/lab08/operating_point.py | tee reports/lab08/operating_point.txt
```

> **Checkpoint.** With the reference model: cost-optimal threshold **0.018**,
> **₹466/claim**, **14.0%** automated; default 0.5 costs ₹6,451/claim; F1-optimal
> 0.225 costs ₹3,771. Your model's numbers will be close if your configuration
> is close. Check that "review everything" is ₹500 exactly, or your cost
> function is wrong.

**4.2 — `D2`.** The script prints the annual figures. Put them in a sentence
each. Say also: **how many times worse than having no model at all is the
default threshold?**

**4.3 — `D3`. How sure are you?** Look at the *bad paid* column at your
cost-optimal threshold. That count is the entire difference between your
model and "review everything". Say how confident you are in the ₹/claim
figure and why. (Stretch 3 turns this into an interval.)

**4.4 — `D4`.** Two sentences to the head of claims operations. No jargon.

> **Done when:** `operating_point.txt` saved and four sentences in your notes.

---

# 5 · Show & tell — three teams, 4 minutes each

Teams are drawn at random, so every team prepares:

1. Your reproducibility table: which conditions, which level (1 min)
2. The leak, and the honest AUC (1 min)
3. Your threshold, its ₹/claim, and your D3 confidence (1 min)
4. **The one result that surprised you** (1 min)

---

## Deliverables checklist

- [ ] Code committed: `labs/lab08/{train.py,params.yaml,inspect_supplied.py,operating_point.py}`,
      `dvc.yaml`, `dvc.lock`, `data/claims/claims.parquet.dvc`, `.dvc/config`,
      `artifacts/lab08/metrics.json`
- [ ] `reports/lab08/`: `rebuild.txt`, `leak.txt`, `repro_checks.txt`,
      `clean_clone.txt`, `teammate.txt`, `operating_point.txt`, `mlflow.png`
- [ ] `reports/lab08/report.md`, at most three pages (README lists its sections)
- [ ] `reports/lab08/CONTRIBUTIONS.md`, signed by all three
- [ ] Tagged and pushed: `git tag lab08 && git push --tags` (on your laptop)
      (every lab is graded at its tag; to move a tag after a late fix: `git tag -f lab08 && git push -f origin refs/tags/lab08`)

---

## If something goes wrong

| Symptom | Cause |
|---|---|
| `NotImplementedError: Part B` | You have not written that function yet. CODE_GUIDE says which |
| `CANNOT COMPARE: ... does not exist` | Training crashed or wrote somewhere else. Scroll up for the traceback |
| `CANNOT COMPARE: ... one of them is stale` | `metrics.json` and `predictions.parquet` come from different runs. Retrain into a fresh `--out` |
| `CANNOT COMPARE: ... different order` | You did not sort the rows, so the two runs scored claims in different orders |
| Two runs differ, n_iter differs | Early stopping is still drawing its validation split at random. Part A2 |
| Two runs identical, shuffled run differs | Your fix covers the seed, not the row order |
| `dvc repro -q` prints nothing and exits 255 | It failed and `-q` hid why. Run `dvc repro` without `-q` |
| `Parameters 'labs/lab08/params.yaml:' are missing from 'params.yaml'` | Flow-style `params: [...]` in `dvc.yaml`. Use block style: one `- labs/lab08/params.yaml:` per line |
| `dvc add`: `output ... is already tracked by SCM (e.g. Git)` | The parquet got committed to git. `git rm --cached data/claims/claims.parquet`, commit, then `dvc add` |
| Clean clone: `dvc pull` fails with missing files | You pushed before `repro`. `dvc push` now, then retry |
| `dvc metrics diff` shows everything as new | `metrics.json` was never committed. `git add artifacts/lab08/metrics.json` |
| `git commit`: "Please tell me who you are" | Set your identity inside the container once (`make check` prints the command). It persists |
| `git push`: authentication failed inside the container | Push from your laptop's terminal instead. The container has no GitHub login, on purpose |
| MLflow page does not load | The UI runs only while `make mlflow` is running. Port is **18500**, not 5000 |
| Teammate's `dvc status` says the data is `modified` | Their `claims.parquet` is not the course file. Recopy it from the Lab 8 zip |

**Stuck for more than ten minutes? Ask.**

---

## The sentence to leave with

> ### If you cannot rebuild it, you do not know what you deployed.
