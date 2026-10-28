# Lab 8 — The Model Is Not the System
**3 hours · Teams of three · Prepared by T5**

> **Read [`OVERVIEW.md`](OVERVIEW.md) first**: why this lab exists, how to
> approach it, the hints, and the map back to T5. Keep
> [`CONCEPTS.md`](CONCEPTS.md) open while you work, and follow
> [`RUNSHEET.md`](RUNSHEET.md) in the room. This file is the brief.

---

## The problem

Aurora's data-science team has handed Platform Engineering (you) a
claims-triage model and a note: *"trained and tested, ready for production,
please wrap it in an API and deploy."* It is meant to auto-approve claims that
will clearly be approved and route the rest to human assessors.

You get `supplied_model/`:

| File | What it is |
|---|---|
| `train_model.py` | The training script, "exported from the notebook" |
| `requirements.txt` | Four package names, no versions |
| `model.pkl` | The trained model |
| `MODEL_CARD.md` | The handover note: accuracy 0.981, AUC 0.997 |

and the data in `data/claims/` (read `DATA_CARD.md`, especially the business
context: **2,000 claims a day, ₹500 per manual review**).

**Before anyone builds an API around this model, find out whether it can be
rebuilt, whether it is honest, and what it is worth, and make the answer to
all three reproducible by someone who is not you.**

---

## Targets

Every number in the last column was measured by running the reference solution
in the course container, the same environment you use.

| What | Target | Supplied model | Reference solution |
|---|---|---|---|
| Two training runs, same laptop | **BIT-IDENTICAL** | 240–300 decisions differ per pair | BIT-IDENTICAL |
| 1 thread vs the default | **BIT-IDENTICAL** | — | BIT-IDENTICAL |
| Same data, rows shuffled | **BIT-IDENTICAL** | — | BIT-IDENTICAL. With a seed alone: 6,554 of 45,365 decisions differ at the operating threshold |
| Clean clone → `dvc pull` → `dvc repro --force` | **BIT-IDENTICAL**, empty `dvc metrics diff` | cannot be rebuilt | BIT-IDENTICAL in about 5 s |
| Two teammates' laptops | **BIT-IDENTICAL** | — | identical on ARM (Apple Silicon) and x86 |
| The leak | named, with **evidence and the timing argument** | AUC 0.997 | AUC drop 0.433 for one feature; next largest 0.007 |
| Honest holdout AUC | reported, not a threshold | — | 0.9218 |
| Operating point | cost-optimal threshold with ₹/claim and automation rate, against "review everything" (₹500) | 0.5 → ₹6,451/claim | 0.018 → **₹466/claim, 14.0%** automated |

**The AUC is reported, not targeted.** A different reasonable configuration
will land near 0.92, above or below. What is graded is that you can say why
it is not 0.997, and that your number rebuilds.

**About the supplied-model column.** Unseeded rebuilds are random, so your
numbers in that column will differ from these. That is the finding. Report
your own, and expect a few hundred differing decisions per pair.

---

## Timetable

| Time | Part | What you do |
|---|---|---|
| 0:00–0:10 | Setup | `make check`, team repo, roles |
| 0:10–0:40 | **A** | The handover: inventory, rebuild, the leak |
| 0:40–1:30 | **B** | Reproducible training: `train.py`, `params.yaml`, every check |
| 1:30–2:10 | **C** | Version all four parts: DVC, MLflow, the clean clone, a teammate's laptop |
| 2:10–2:45 | **D** | The operating point, in rupees |
| 2:45–3:00 | Show & tell | Three teams, drawn at random |

---

## Part A — The handover (30 min)

**A1. The inventory.** A deployed model is four things: **code, data, weights,
environment** (T5 §1). For each, write down what the handover pins exactly,
what it pins loosely, and what it leaves out. Be specific: "the data" is not
an answer; "a relative path, with no hash or date" is.

**A2. Rebuild it.** `python labs/lab08/rebuild.py` runs the unchanged script
three times and compares every build with the others and with the shipped
pickle. Report the table, and translate the worst pair into customers per day.
Then explain why `n_iter` changes between runs of identical input. You will
need the scikit-learn documentation for this estimator.

**A3. The leak.** Write `importance()` in `inspect_supplied.py` and run it.
Report the top features by AUC drop. For the top one, make the **timing
argument**: at the moment the model has to decide on a claim, does this value
exist yet? Evidence without the argument, or the argument without evidence,
is half an answer.

**A4. The baseline.** The card says accuracy 0.981. What does "approve
everything" score on the same holdout? What does that tell you about accuracy
as a headline metric here?

---

## Part B — Reproducible training (50 min)

**B1. `params.yaml`.** It starts as a faithful transcription of the supplied
script, flaws included. Make it the single place where everything that can
change the model lives: add what is missing, and remove what the model must
not see (with a comment saying why).

**B2. `train.py`.** Write `load_data()`, `prep()` and `build_model()`
([`CODE_GUIDE.md`](CODE_GUIDE.md)). Train twice. `check_reproducible.py`
must say **BIT-IDENTICAL**.

**B3. Threads.** Train with `OMP_NUM_THREADS=1` and compare with the default.

**B4. Row order.** Train on a shuffled copy of the same rows (`--data`). Measure
it **twice**: once with only the seed, once with your fix. Report both, and the
number of decisions that differ at your Part D threshold when only the seed is
set.

**B5. Category order.** The supplied script let pandas infer categories. Is
that a source of disagreement for *this* model and *these* library versions?
Test it and report what you find, including if it is nothing.

**B6. The honest model.** Holdout AUC and accuracy at 0.5, beside the supplied
model's and beside "approve everything".

---

## Part C — Version all four parts (40 min)

**C1. Data under DVC.** `dvc init`, `dvc add` the claims file, add the team's
DVC remote, commit the pointer.

**C2. The pipeline.** Write `dvc.yaml` with one stage, `train`, that declares
its command, dependencies, params file, outputs and metrics. `dvc repro`, then
commit `dvc.lock` and `metrics.json`, then `dvc push`, **in that order**.

**C3. Experiments in MLflow.** Log at least two runs: the parameters as
handed over (`params.supplied.yaml`, a frozen copy: leak in, no seed) and
yours. Open the UI (`make mlflow`,
<http://localhost:18500>), compare them, and take a screenshot.

**C4. The clean clone.** Clone the team repo into a fresh folder, `dvc pull`,
`dvc repro --force`, and compare with `check_reproducible.py`. Also show that
`dvc metrics diff` and `git status` are both empty.

**C5. A teammate's laptop.** A second teammate clones the repo on their own
machine and rebuilds. Compare fingerprints. If your team has both an Apple
Silicon and an Intel/AMD laptop, say so. That is a stronger test.

---

## Part D — The operating point (35 min)

The process: a claim with `p_reject < t` is auto-approved (if it should have
been rejected, Aurora pays its `claim_amount`); otherwise an assessor reviews
it for ₹500.

**D1.** Write `cost_at()` and `choose_thresholds()` in `operating_point.py`.
Report the policy table: review everything, approve everything, 0.5,
F1-optimal, cost-optimal. For each: threshold, ₹/claim, automation rate, bad
claims paid.

**D2.** Annualise at 2,000 claims a day: what does the cost-optimal threshold
save against reviewing everything, and what would choosing the F1-optimal
threshold have cost instead?

**D3. How sure are you?** How many bad claims are paid at your cost-optimal
threshold? What does that do to your confidence in its ₹/claim figure?

**D4. The recommendation.** Two sentences to Aurora's head of claims
operations: deploy or not, at what threshold, and what it will and will not
do. No jargon; one number per sentence at most.

---

## Deliverables

Committed to your team repo and tagged **`lab08`**:

1. **Code:** `labs/lab08/train.py`, `params.yaml`, `inspect_supplied.py`,
   `operating_point.py`, plus `dvc.yaml`, `dvc.lock`,
   `data/claims/claims.parquet.dvc`, `.dvc/config`,
   `artifacts/lab08/metrics.json`
2. **Evidence,** in `reports/lab08/`, the raw output of each command, saved with
   `| tee` (see the runsheet): `rebuild.txt`, `leak.txt`, `repro_checks.txt`,
   `clean_clone.txt`, `teammate.txt`, `operating_point.txt`, and
   `mlflow.png`
3. **`reports/lab08/report.md`**, at most three pages:
   - the A1 inventory and the A2 rebuild table, with the `n_iter` explanation
   - the leak: evidence, timing argument, honest vs supplied numbers
   - a **reproducibility table**: each condition (runs, threads, row order,
     category order, clean clone, teammate) with the level achieved
   - the policy table, the annualised figures, and D3's confidence statement
   - the D4 recommendation
   - one thing that surprised you, and one negative result
4. **`reports/lab08/CONTRIBUTIONS.md`**: who did what, signed by all three.
   Individual marks may be adjusted where it disagrees with the commit history.

---

## Rubric (4% of the course)

| Criterion | Weight | Full marks means |
|---|---|---|
| Reproducibility | 30% | Bit-identical across runs, threads, row order, the clean clone and a teammate's laptop, each with the checker's output; the level named correctly for anything that is not bit-identical |
| Versioning | 20% | Data in DVC not git; one `dvc.yaml` stage with params and metrics; lock and metrics committed; remote populated; MLflow comparison of leaky vs honest |
| The leak | 15% | Evidence **and** timing argument; honest numbers beside the supplied ones |
| The operating point | 25% | Correct cost function; full policy table; annualised figures; a D3 answer that engages with how few claims decide it; a D4 a non-specialist could act on |
| Honesty | 10% | Every claim has a number; at least one negative result reported plainly |

Module 1's rules carry over: **no number, no claim**. Fabricated numbers score
zero. **Honest negative results score full marks.**

---

## Stretch

1. **Outside the container.** One teammate runs `train.py` natively on their
   laptop, outside Docker, with the same pinned versions (`uv sync --frozen`
   on the host). Compare with `check_reproducible.py --threshold 0.5
   --threshold <yours>`. Which level do you get? The reference measured 58 of
   45,365 probabilities differing between macOS and Linux, all in the 17th
   decimal place.
2. **The other fix.** There are two ways to remove the early-stopping
   randomness. Implement the one you did not choose, check it is reproducible,
   and put it through Part D. Report the difference in ₹ per year.
3. **Bootstrap the operating point.** Resample the holdout 1,000 times, recompute
   the cost-optimal threshold and its ₹/claim each time, and report the
   interval. Does it still beat reviewing everything?
4. **Sensitivity.** Re-run Part D with a review cost of ₹300 and of ₹1,000.
   How far does the threshold move, and does the answer to D4 change?
