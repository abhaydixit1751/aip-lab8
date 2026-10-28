# Lab 8 — Concepts
### Keep this open while you work

| Concept | In the code | In the theory |
|---|---|---|
| The artefact problem | `supplied_model/`, your A1 inventory | T5 §1 |
| Three levels of "the same model" | `check_reproducible.py` | T5 §2 |
| The prediction fingerprint | `train.py::fingerprint` | T5 §2 |
| Where nondeterminism hides | `load_data`, `prep`, `build_model` | T5 §2.2 |
| Early stopping's hidden split | `build_model` | T5 §2.2 |
| Category order | `prep` | T5 §2.2 |
| Leakage and the timing argument | `params.yaml`, `inspect_supplied.py` | T5 §4 |
| Permutation importance | `inspect_supplied.py::importance` | T5 §4 |
| Accuracy under imbalance | `inspect_supplied.py` output | T5 §5 |
| git · DVC · MLflow: who versions what | `.dvc/`, `dvc.yaml`, `mlflow.db` | T5 §3 |
| A DVC stage | `dvc.yaml`, `dvc.lock` | T5 §3 |
| The clean-clone test | Part C4 | T5 §3 |
| The container as the environment pin | `docker/dev.Dockerfile`, `uv.lock` | T5 §7 |
| The operating point | `operating_point.py` | T5 §5 |

---

## The artefact problem

**What it is.** A model in production is four things: the **code** that
trained it, the **data** it was trained on, the **weights** it learned, and the
**environment** (Python, libraries, operating system) that ran the code. Change
any one and you may get a different model. A typical handover versions the
code in a notebook export and ships the weights as a pickle. The data and the
environment are left implicit.

**In this lab.** `requirements.txt` names four packages and no versions. The
data is a relative path with no hash. The weights are a pickle with no record
of what produced it. The code has no seed. Your A1 inventory is this table
filled in honestly.

---

## Three levels of "the same model"

| Level | Means | How you check it |
|---|---|---|
| **Bit-identical** | every probability for every claim is the same `float64` | fingerprints equal |
| **Decision-identical** | probabilities differ, but no claim changes decision at the thresholds you care about | count flips at each threshold |
| **Metric-identical** | the AUC or accuracy matches to a few decimals | weakest. Two very different models can share an AUC |

**Which one to promise** depends on who is asking. An auditor re-running last
quarter's decisions needs decision-identical at the deployed threshold. A CI
pipeline checking "did this refactor change the model?" wants bit-identical,
because it is the only level with no tolerance to argue about. **Say which
level you are claiming.** "Reproducible" alone means nothing.

**The fingerprint.** `train.py` hashes the raw bytes of every predicted
probability, in a fixed claim order, with SHA-256. Two runs have the same
fingerprint if and only if every probability is bit-identical. It is cheap,
it is exact, and it is one string you can commit, log to MLflow, and compare
in `dvc metrics diff`.

---

## Where nondeterminism hides: measured on this model

Everything below was measured with the reference solution in the course
container. **Some textbook causes bite here and some do not.** Your job in
Part B is to find out which, not to recite the list.

| Source | Real here? | Measured |
|---|---|---|
| No seed + early stopping | **yes** | 240–300 of 45,365 decisions differ between unseeded builds |
| Row order, with a seed | **yes** | shuffled file: n_iter 87 vs 67; of 45,365 claims, 338 decisions differ at 0.5 and 6,554 at 0.018 |
| Thread count | no | 1, 4 and the default thread count: bit-identical |
| Category order | no | inferred, explicit, even reversed: 0 probabilities differ |
| Python patch version (3.12.11 vs 3.12.14) | no | bit-identical |
| Operating system (macOS vs Linux, same pins) | **in the last bits** | 58 of 45,365 probabilities differ, by at most 5.6 × 10⁻¹⁷; 0 decisions |
| CPU architecture (ARM vs x86, both Linux) | no | bit-identical |

---

## Early stopping's hidden split

**What it is.** `HistGradientBoostingClassifier` has `early_stopping="auto"`,
which **switches itself on when there are more than 10,000 training rows**.
It then holds out `validation_fraction` (10%) of the training rows, watches the
validation loss, and stops adding trees when the loss stops improving.

**Why it breaks reproducibility.** Which 10% gets held out is drawn at random.
With no `random_state`, it is a different 10% every run, so training stops at
a different iteration (A2's `n_iter` column) and the model differs.

**Two ways out.** Fix the draw (`random_state`), or turn early stopping off.
Both are reproducible. They are **not the same model**, and the difference is
worth measuring in Part D (stretch 2).

**Why row order still matters with a seed.** The seed fixes *which positions*
are held out. If the rows arrive in a different order, the same positions hold
different claims. Fixing the order ("sort by a stable key before anything
else") closes that gap.

---

## Category order

**The textbook trap.** Many tree libraries split on a categorical's integer
*codes*. `astype("category")` builds the codes from whatever values are
present, so a subset missing one value (or a single-row request in Lab 9)
could silently renumber the others, and a split on "code 2" would mean a
different plan.

**What was measured here.** scikit-learn 1.9.1 with
`categorical_features="from_dtype"` encodes categories **by value**, not by
position. Inferred, explicit and reversed orders all gave 0 differing
probabilities, and so did one-row frames. **On this model, with these
versions, the trap does not fire.**

**So why write explicit categories anyway?** You may still choose to, because
it documents what the model expects and does not depend on a library
behaviour that has changed before. That is a defensible choice. "We fixed it
because it was broken" is not, because it was not. Report what you measured.

---

## Leakage and the timing argument

**What it is.** A feature **leaks** when its value is not available at the
moment the model has to make its prediction, typically because it is written
*after* the event being predicted, or *by* it. The model learns the
after-effect of the label rather than any cause of it.

**The signature.** Scores that are too good (0.997 on a messy business
problem) with **one feature carrying almost all of the weight**.

**The argument you must make.** Evidence alone (the model relies on X) does
not prove a leak: sometimes one feature really is that predictive. What
proves it is the **timing**: *who writes this value, and when, relative to the
decision the model is meant to make?* If the answer is "after", the feature
cannot be used, however predictive it is.

**Why it matters beyond this lab.** In Lab 11 you meet its sibling: a feature
that *is* available at decision time but is computed **differently** there.
Same question, subtler answer.

---

## Permutation importance

**What it is.** Take the fitted model and the holdout. Shuffle one column,
breaking its relationship with the label, and re-score. The drop in the metric
is how much the model depends on that column. Repeat a few times per column
and average.

```python
from sklearn.inspection import permutation_importance
r = permutation_importance(model, X, y, scoring="roc_auc",
                           n_repeats=5, random_state=0)
r.importances_mean        # one number per column, in X.columns order
```

**Why this rather than the usual "feature importance plot".** It is measured
on held-out data, in the metric you care about, and works for any model.
Impurity-based importances, the usual plot, are computed on training data
and are biased toward features with many distinct values.

**Caveat.** Correlated features share importance: shuffle one and the model
leans on its twin. That is not what happens here. The top feature drops the
AUC by 0.43 and the next by 0.007.

---

## Accuracy under imbalance

About 83% of holdout claims are approved (86% across the whole dataset). A
"model" that approves everything scores ~0.83 accuracy while catching zero bad
claims. Accuracy is dominated by the majority class, so the card's 0.981 has
to be read against 0.834, not against 0.5. This is also why F1, AUC and above
all **cost** are the metrics in this lab.

---

## git · DVC · MLflow: who versions what

| Part of the artefact | Versioned by | What is committed to git |
|---|---|---|
| Code, params, pipeline definition | **git** | the files themselves |
| Data | **DVC** | a small `.dvc` pointer: the file's md5 and size |
| Model outputs | **DVC** (pipeline outs) | `dvc.lock`: the md5 of every input and output of the last run |
| Metrics | git (small JSON, `cache: false`) | `metrics.json`, so `dvc metrics diff` can compare commits |
| Experiments you tried | **MLflow** | nothing; `mlflow.db` is a local lab notebook |
| Environment | **the container** + `uv.lock` | `uv.lock`, `docker/dev.Dockerfile` |

**How DVC works, in one paragraph.** `dvc add file` computes the file's md5,
moves the bytes into a content-addressed **cache** (`.dvc/cache`), and writes
`file.dvc` containing the hash. You commit the pointer, not the bytes.
`dvc push` copies cache entries to a **remote**, and `dvc pull` fetches the
entries the current commit's pointers name. Git carries *which* version;
DVC carries *the bytes*.

**DVC vs MLflow.** DVC answers "what exactly produced the model in this
commit?". It is the record of what you ship. MLflow answers "what did we try
this week, and how did each do?". It is the record of what you explored. The
DVC stage runs with `--no-mlflow` so a pipeline rebuild does not pollute the
experiment log.

---

## A DVC stage

A pipeline stage declares everything it reads and writes, so DVC can tell
whether it needs to rerun and can record exact hashes in `dvc.lock`. The
shape, for a *different* stage than yours:

```yaml
stages:
  featurize:
    cmd: python src/featurize.py --config configs/features.yaml --out build/features
    deps:
      - data/raw/events.parquet
      - src/featurize.py
    params:
      - configs/features.yaml:          # a params file that is NOT ./params.yaml
    outs:
      - build/features/table.parquet
    metrics:
      - build/features/stats.json:
          cache: false                  # small, committed to git, diffable
```

`dvc repro` reruns a stage only if a dep, a param or the command changed, and
`--force` reruns anyway. After it runs, **commit `dvc.lock`**: that file is the
receipt.

> ⚠️ **Write every list in block style**, one item per line, as above. In
> flow style, `params: [configs/features.yaml:]` is read as a parameter
> *named* `configs/features.yaml:` inside the default `./params.yaml`. The
> reference stage failed with `Parameters '...' are missing from
> 'params.yaml'`, and under `dvc repro -q` it failed **silently** (no output,
> exit code 255).

---

## The clean-clone test

The strongest test available to one team: `git clone` into an empty folder,
`dvc pull`, `dvc repro --force`, and compare the result with the original.
The clone knows only what is committed and pushed, so anything you forgot to
version shows up here as a failure. The usual ones:

- data never `dvc push`ed, or pushed before `repro` so the model is missing
- `metrics.json` ignored by git, so `dvc metrics diff` has nothing to compare
- a path counted from the script's location (`parents[2]`) that breaks when
  the checkout lives somewhere else. Find the root by searching up for
  `pyproject.toml`, as the provided code does

---

## The container as the environment pin

`uv.lock` pins every Python package to an exact version and hash. It cannot
pin the operating system's maths libraries, the compiler the wheels were built
with, or the OpenMP runtime, and those differ between macOS and Linux builds
of the same package version. Measured with identical pins:

| Where `train.py` ran | Fingerprint |
|---|---|
| Course container, Linux on ARM (Apple Silicon) | `f39f014c…` |
| Course container, Linux on x86 (Intel/AMD) | `f39f014c…` |
| Course container, Python 3.12.11 instead of 3.12.14 | `f39f014c…` |
| macOS natively, same pins | `361ce589…`: 58 probabilities differ in the 17th decimal place; 0 decisions |

The dividing line is the **operating system**, not the CPU. That is why every
laptop in this course runs the same Linux image.

---

## The operating point

**The decision.** For each claim the model outputs `p` = probability it should
be rejected. Pick a threshold `t`:

| | Cost to Aurora |
|---|---|
| `p < t` → auto-approve; claim was fine | ₹0 |
| `p < t` → auto-approve; claim **should have been rejected** | its `claim_amount` (mean ≈ ₹98,000) |
| `p ≥ t` → assessor reviews it | ₹500 |

`cost(t)` is the sum over the holdout. Divide by the number of claims for
₹/claim, which you can compare directly with "review everything" (₹500) and
"approve everything".

**Why not F1?** F1 weighs a false positive and a false negative equally. Here
one costs ₹500 and the other about ₹98,000, a ratio of **197 : 1**. Maximising
F1 buys automation with money: the reference's F1-optimal threshold
auto-approves 84% of claims and pays out 158 bad ones.

**The shape of the curve.** At very low `t`, almost everything goes to review,
so cost ≈ ₹500/claim. As `t` rises, cheap reviews are replaced by
auto-approvals. That helps until the first expensive bad claims slip through,
and then it hurts fast. With costs this asymmetric the optimum sits at a very
low threshold and automates only a slice of the queue.

**How few claims decide it.** At the reference optimum only **4** bad claims
are paid on the 3,796-claim holdout. The whole margin over "review everything"
(₹34/claim) rests on those few, so move one of them and the answer moves.
Say so in D3. Stretch 3 measures it.

**Annualising.** ₹/claim × 2,000 claims/day × 365. 1 crore = 10⁷ rupees.
