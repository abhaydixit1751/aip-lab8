# Lab 8 — the code: what is written for you, and what is yours

Seven files in `labs/lab08/`, plus one you create at the repo root. This page
documents them so you spend the lab on the questions rather than on reading
scaffolding.

| File | Status | Part |
|---|---|---|
| `rebuild.py` | **provided**, run as is | A2 |
| `inspect_supplied.py` | provided + **one function yours**: `importance()` | A3 |
| `params.yaml` | **yours to edit** (starts as a transcription of the supplied script) | B1 |
| `params.supplied.yaml` | provided, **do not edit**: a frozen copy of the starting `params.yaml` | C3 |
| `train.py` | provided + **three functions yours**: `load_data()`, `prep()`, `build_model()` | B2 |
| `check_reproducible.py` | **provided, do not weaken it** | B, C |
| `operating_point.py` | provided + **two functions yours**: `cost_at()`, `choose_thresholds()` | D |
| `dvc.yaml` (repo root) | **yours, from scratch** | C2 |

**The contract** is the same as Module 1's: in every file, everything above the
`YOURS` banner is provided and correct, and everything below it raises
`NotImplementedError` until you write it. Every script finds the repo root by
searching upward for `pyproject.toml`, so they work from any directory, in a
clean clone, and in `/tmp`.

---

## 1 · `rebuild.py` (provided)

```bash
python labs/lab08/rebuild.py              # 3 rebuilds, ~15 s
python labs/lab08/rebuild.py --runs 5
```

Copies `supplied_model/train_model.py` **unmodified** into a scratch folder,
runs it N times, and scores all 45,365 claims with every resulting model and
with the shipped `model.pkl`. It prepares features exactly as the supplied
script does, driven by the model's own `feature_names_in_`.

| Column | Meaning |
|---|---|
| `n_iter` | trees actually built before early stopping |
| `probs differ` | claims whose probability is not bit-identical |
| `max \|dp\|` | largest probability change on any one claim |
| `decisions` | claims whose decision flips at `--threshold` (default 0.5) |
| `per day` | `decisions / 45,365 × 2,000`: customers a day |

---

## 2 · `train.py`

```bash
python labs/lab08/train.py                                  # params.yaml beside it, MLflow on
python labs/lab08/train.py --out /tmp/run1 --no-mlflow      # where to write; skip MLflow
python labs/lab08/train.py --params labs/lab08/params.supplied.yaml --out /tmp/x
python labs/lab08/train.py --data /tmp/shuffled.parquet --out /tmp/shuf --no-mlflow
```

### Provided

| Function | What it does |
|---|---|
| `find_root()` | repo root = nearest ancestor with `pyproject.toml` |
| `load_params(path)` | reads YAML; guarantees `features.boolean` exists |
| `fingerprint(probs)` | SHA-256 of the `float64` bytes, in the order given |
| `environment()` | Python, OS, CPU, library versions, `OMP_NUM_THREADS`, in-container flag |
| `log_to_mlflow(p, metrics, out)` | one run in experiment `lab08-claims-triage`, tracking to `mlflow.db` at the repo root |
| `main()` | the flow below |

`main()` does, in order:

1. `df, train, hold = load_data(p)`, **yours**
2. `model = build_model(p)`, **yours**, then `model.fit(prep(train, p), train[label])`
3. predicts on the holdout (for metrics) and on **all** of `df` (for the fingerprint)
4. writes `model.joblib`, `predictions.parquet` (`claim_id`, `p_reject`, in
   `df`'s row order) and `metrics.json`
5. logs to MLflow unless `--no-mlflow`

`metrics.json` holds `holdout_auc`, `holdout_accuracy_at_0.5`,
`holdout_reject_rate`, `n_iter`, `prediction_fingerprint` and `environment`.

### Yours

**`load_data(p) -> (df, train, hold)`**
Read `p["data"]["path"]` (relative to the repo root; `--data` makes it absolute,
and `ROOT / absolute_path` does the right thing). Split by `month_index` using
`train_months` and `holdout_months` from params, both inclusive. `df` is what
gets fingerprinted, so **its row order must not depend on how the file was
written.**

**`prep(rows, p) -> X`**
Columns in the order numeric, categorical, boolean, as listed in params.
Categoricals as pandas `category` dtype; booleans as `int`. Read CONCEPTS,
"Category order", then decide how to build the categories, and test your
decision in B5.

**`build_model(p) -> estimator`**
An unfitted `HistGradientBoostingClassifier(categorical_features="from_dtype", ...)`.
Everything else comes from params: `p["model"]["hyperparameters"]` as keyword
arguments, plus whatever makes it deterministic. No literals.

> **What "done" looks like.** Two runs into two `--out` folders;
> `check_reproducible.py` says `BIT-IDENTICAL`; `holdout_auc` is near 0.92,
> not 0.997.

---

## 3 · `inspect_supplied.py`

```bash
python labs/lab08/inspect_supplied.py
```

**Provided:** loads the shipped `model.pkl`, prepares the holdout the way the
supplied script does, prints the supplied model's AUC and accuracy and the
approve-everything accuracy, then prints the top 8 of whatever
`importance()` returns.

**Yours:** `importance(model, X, y) -> list[(feature, mean AUC drop)]`, largest
first. `permutation_importance` with `scoring="roc_auc"`, a fixed
`random_state`, a few repeats. About 5 lines. Takes ~4 s.

---

## 4 · `check_reproducible.py` (provided)

```bash
python labs/lab08/check_reproducible.py FOLDER_A FOLDER_B
python labs/lab08/check_reproducible.py FOLDER_A FOLDER_B --threshold 0.5 --threshold 0.018
```

Each folder is a `train.py --out`. The script prints both environments side
by side (differences marked) and both fingerprints, then one verdict:

| Verdict | Exit code |
|---|---|
| `BIT-IDENTICAL` | 0 |
| `DECISION-IDENTICAL at the threshold(s) checked` | 1 |
| `DIFFERENT` | 1 |
| `CANNOT COMPARE: <reason>` | 2 |

**It refuses**, with a reason, when a file is missing; `metrics.json` is not
JSON; the fingerprint is missing, empty, or not 64 hex characters;
`predictions.parquet` is empty, has missing values, or has the wrong columns;
the fingerprint in `metrics.json` does not match the hash of the
predictions beside it (stale); or the two runs scored different claims or in a
different order.

> **Why it is this strict.** The first version, written while building the
> reference solution, compared two fingerprints that were both empty because
> training had crashed, and reported "bit-identical". A check that can pass on
> nothing is worse than no check. Do not edit this file to make it pass.

---

## 5 · `operating_point.py`

```bash
python labs/lab08/operating_point.py
```

Reads `artifacts/lab08/predictions.parquet`, which is the pipeline's output,
so **run `dvc repro` (or `train.py` with the default `--out`) first**. It keeps
the holdout months only, and writes `artifacts/lab08/operating_point.json`.

**Provided:** `load_holdout()`, `describe()` (one row of the policy table),
the table, the annual figures, constants `REVIEW_COST = 500`,
`CLAIMS_PER_DAY = 2_000`, and `GRID`, the 999 thresholds to try
(0.001 to 0.999 in steps of 0.001, so 0.5 is included).

**Yours:**

- `cost_at(t, p, y, amount) -> float`: total rupees at threshold `t`. Two terms.
  `y == 1` means *should have been rejected*.
- `choose_thresholds(p, y, amount) -> (t_cost, t_f1)`: the `GRID` value with
  the lowest cost, and the one with the highest F1, where "sent to review"
  (`p >= t`) is the positive prediction.

> **Sanity check.** Your `cost_at` at a threshold of 0 must give exactly ₹500 ×
> the number of holdout claims. If it does not, one of the two terms is wrong.

---

## 6 · `dvc.yaml` (repo root, yours)

One stage named `train`. It must declare:

| Key | Contains |
|---|---|
| `cmd` | `python labs/lab08/train.py --params labs/lab08/params.yaml --out artifacts/lab08 --no-mlflow` |
| `deps` | the claims parquet, and `train.py` |
| `params` | `labs/lab08/params.yaml:` (not the default `params.yaml`) |
| `outs` | `model.joblib` and `predictions.parquet` under `artifacts/lab08/` |
| `metrics` | `artifacts/lab08/metrics.json` with `cache: false` |

CONCEPTS, "A DVC stage", shows the shape on a different example. **Block
style, one item per line.**

---

## What you must not change

- `check_reproducible.py`, in any way
- `params.supplied.yaml`
- the `fingerprint()` function and the `predictions.parquet` format, because
  the checker and Lab 9 depend on them
- anything in `supplied_model/` or `data/`
