# T5 — What Breaks Between the Notebook and Production
**AI in Practice 2 · Theory 5 · 90 minutes · Week 1**

> **Prepares you for:** Labs 8 and 9
> **Assumes from MLEF and Module 1:** training and evaluating a classifier, AUC,
> precision and recall, a Python environment, calling an HTTP API. We are going
> to take one ordinary model and find everything that stops it being a product.
>
> **Not assumed:** git with a team, DVC, MLflow and Docker. No earlier course
> teaches them; §3 and §7 introduce them, and Lab 8 is where you first use them.
> Before Lab 8, work through the "Try it" exercises in
> [`docs/toolkit/git-and-github.md`](../docs/toolkit/git-and-github.md) and
> [`docs/toolkit/dvc-and-mlflow.md`](../docs/toolkit/dvc-and-mlflow.md) (about ten
> minutes each, in the course container).

---

## Running order

| Min | Segment |
|---|---|
| 0–8 | §1 The artefact problem |
| 8–22 | §2 Reproducibility is a testable property |
| 22–35 | §3 Versioning code, data and experiments |
| 35–45 | §4 What the model may know: leakage and skew |
| 45–58 | §5 The prediction as a product: the operating point |
| 58–68 | §6 Serving: the contract |
| 68–78 | §7 Containers: what an image guarantees |
| 78–85 | §8 Load, latency and batching |
| 85–90 | Labs 8–9 briefing |

Every number in this lecture was measured on the course's own claims model, in
the course container. You will reproduce most of them this week.

---

## 1. The artefact problem

The claims-triage model you meet in Lab 8 arrives the way most models arrive:
a training script exported from a notebook, a `requirements.txt` with four
package names, a pickle, and a note saying "accuracy 0.981, AUC 0.997, ready
for production". Nothing about it is unusual. That is the point.

### 1.1 A model is four things

| Part | What it is | How the handover versioned it |
|---|---|---|
| **Code** | the training script and its preprocessing | a notebook export; no seed |
| **Data** | the exact rows it was trained on | a relative path, no hash, no date |
| **Weights** | the fitted parameters | a pickle with no record of what produced it |
| **Environment** | Python, libraries, OS, maths libraries | four unpinned package names |

Change any one of the four and you may get a different model. In most
notebooks, three of the four are unversioned, and the one that is versioned
(the code) is versioned by accident.

### 1.2 Why this is an engineering problem, not a tidiness problem

Sculley et al. called it *hidden technical debt*: in a real ML system the model
code is a small box in the middle of a large diagram of data collection,
feature extraction, configuration, serving and monitoring. The debt lives in
the diagram, not in the box. It is paid when:

- an auditor asks which model made a decision last March
- a bug fix to preprocessing needs the model retrained *identically except for
  the fix*
- two teams disagree about whether a metric moved, and neither can rebuild the
  other's number
- the person who trained it has left

None of those can be answered from a pickle.

---

## 2. Reproducibility is a testable property

"Reproducible" is usually used as an adjective of approval. In this course it
is a **property with a test**, and the test has three possible answers.

### 2.1 Three levels of "the same model"

| Level | Means | Checked by |
|---|---|---|
| **Bit-identical** | every predicted probability, for every input, is the same float | a hash of the predictions |
| **Decision-identical** | probabilities differ, but no decision changes at the thresholds in use | counting flips per threshold |
| **Metric-identical** | the headline metric matches to a few decimals | comparing numbers |

Metric-identical is the weakest and most commonly claimed. Two models can
share an AUC to four decimals and disagree on hundreds of individual
decisions. The customer whose claim flipped is not comforted by the AUC.

**Which level to promise depends on who is asking.** A CI pipeline asking "did
this refactor change the model?" wants bit-identical, the only level with no
tolerance to argue about. An auditor re-running last quarter's decisions needs
decision-identical at the deployed threshold. Say which level you are
claiming; "reproducible" alone means nothing.

**The fingerprint.** Hash the raw bytes of every predicted probability, in a
fixed input order, with SHA-256. Equal hashes ⇔ bit-identical predictions. It
is one string you can commit, log, and compare.

### 2.2 Where nondeterminism hides, measured

The supplied claims script, run three times on identical input:

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| trees built (`n_iter`) | 91 | 105 | 79 |
| decisions that differ from another run (of 45,365) | 244–299 per pair | | |

At 2,000 claims a day, that is **about a dozen customers a day** whose outcome
depends on which build of "the same model" was deployed. Nobody changed
anything.

The cause is one line of scikit-learn documentation: `HistGradientBoostingClassifier`
turns on **early stopping automatically above 10,000 rows**, holding out a
random 10% of training data, and the script sets no seed. Here is the full
audit on this model:

| Suspected source | Bites here? | Measured |
|---|---|---|
| No seed + early stopping | **yes** | 240–300 decisions differ per pair of builds |
| Row order, *with* a seed | **yes** | same rows shuffled: 6,554 of 45,365 decisions differ at the operating threshold |
| Thread count | no | 1, 4, default: bit-identical |
| Category order | no | inferred, explicit, reversed: 0 probabilities differ |
| Python patch version | no | 3.12.11 vs 3.12.14: bit-identical |
| CPU architecture (ARM vs x86, Linux) | no | bit-identical |
| Operating system (macOS vs Linux, same pins) | **last bits only** | 58 probabilities differ by ≤ 5.6 × 10⁻¹⁷; 0 decisions |

Three lessons in one table.

1. **A seed is necessary and not sufficient.** The seed fixes *which positions*
   go to the validation split; if the rows arrive in a different order, those
   positions hold different claims. Sort by a stable key first.
2. **Test the trap before you fix it.** Category-order bugs are real in many
   libraries and in older scikit-learn. In 1.9.1 they measure as zero. A fix
   for a problem you did not demonstrate is not engineering.
3. **The dividing line is the operating system, not the CPU.** With every
   Python package pinned identically, macOS and Linux differ in the 17th
   decimal place, because the platform builds of the numerical wheels differ
   (compiler, OpenMP runtime, `libm`). Linux on ARM and Linux on x86 agree
   bit for bit. This is the argument for §7.

---

## 3. Versioning code, data and experiments

### 3.1 Who versions what

![Who versions what: git carries which version (code, params, the dvc.yaml recipe, the dvc.lock receipt, metrics, and a small pointer for the data); the DVC cache holds the bytes, filed by md5; the DVC remote holds the bytes for others (push and pull); MLflow records what you tried; the container and uv.lock pin everything else. The clean clone: git clone, dvc pull, dvc repro --force, dvc metrics diff; nothing printed means the same model.](../decks/infographics/versions.svg)

| Part | Tool | What is committed to git |
|---|---|---|
| Code, parameters, pipeline definition | **git** | the files |
| Data | **DVC** | a small pointer: the file's hash and size |
| Model outputs | **DVC** pipeline | `dvc.lock`: the hash of every input and output of the last run |
| Metrics | git (small JSON) | the file, so it can be diffed between commits |
| Experiments you tried | **MLflow** | nothing; a local run database |
| Environment | lockfile + **container image** | `uv.lock`, the Dockerfile |

**Why not put the data in git?** Git stores every version of every file
forever and diffs them line by line. It works for code and fails for
gigabytes of binary. DVC keeps the bytes in a content-addressed cache and a
**remote** (S3, GCS, Azure Blob; a local folder in the lab), and lets git carry
only the hash. Git answers *which version*; DVC carries *the bytes*.

### 3.2 A pipeline is a declaration

A DVC stage declares its command, its dependencies, its parameters and its
outputs. From that, DVC can answer "is this output stale?" without running
anything, and `dvc.lock` records exactly which bytes produced which bytes.

```yaml
stages:
  train:
    cmd: python labs/lab08/train.py --params labs/lab08/params.yaml --out artifacts/lab08 --no-mlflow
    deps:
      - data/claims/claims.parquet
      - labs/lab08/train.py
    params:
      - labs/lab08/params.yaml:          # a params file that is not ./params.yaml
    outs:
      - artifacts/lab08/model.joblib
      - artifacts/lab08/predictions.parquet
    metrics:
      - artifacts/lab08/metrics.json:
          cache: false                   # small; committed to git; diffable
```

> **Write it in block style, as above.** In flow style,
> `params: [labs/lab08/params.yaml:]` is read as a parameter *named*
> `labs/lab08/params.yaml:` inside the default `params.yaml`. The reference
> stage failed on exactly this, and under `dvc repro -q` it failed with no
> output at all.

### 3.3 DVC is not MLflow

- **DVC** answers: *what exactly produced the model in this commit?* It is the
  record of what you **ship**.
- **MLflow** answers: *what did we try this week, and how did each do?* It is
  the record of what you **explored**: parameters, metrics, tags, artefacts per
  run, with a UI to compare them.

Use both, and do not let them overlap: the pipeline stage runs with MLflow
logging off, so a rebuild does not pollute the experiment log.

### 3.4 The test: a clean clone

The strongest test one team can run on itself: `git clone` into an empty
folder, `dvc pull`, `dvc repro --force`, compare fingerprints. The clone knows
only what was committed and pushed, so everything you forgot to version shows
up as a failure. On the reference: **bit-identical, about 5 seconds, clone to
verdict.**

A check that can pass on nothing is worse than no check. The first version of
the reference's comparison script compared two fingerprints that were both
empty, because training had crashed, and reported "bit-identical". Two empty
strings are equal. The version you get refuses to compare a missing, empty,
malformed or stale fingerprint.

---

## 4. What the model may know: leakage and skew

### 4.1 Leakage

A feature **leaks** when its value is not available at the moment the model
must decide, usually because it is written *after* the event being predicted,
or *by* it (Kaufman et al.). The model learns the after-effect of the label.

**The signature:** a score too good for the problem, with one feature carrying
nearly all of the weight. The supplied claims model scores AUC 0.997. Shuffle
one column, `assessor_note_length`, and the AUC drops by **0.433**. Shuffle
the next most important column and it drops by **0.007**.

**The argument that proves it is about time, not statistics.** Who writes the
assessor's case note, and when? The assessor, *while deciding the claim*. The
model's entire purpose is to decide before an assessor sees the claim. So the
feature cannot exist at prediction time, however predictive it is. Remove it:
AUC **0.9218**. That is the honest model: useful and unremarkable.

### 4.2 Skew: leakage's quieter sibling

**Training–serving skew** is a feature that *does* exist at decision time but
is **computed differently** there than in training: a different time window, a
different join, a different default for missing values. Offline evaluation
cannot see it, because offline both sides use the training computation. You
meet it in Lab 11, and it costs recall at exactly the operating point you
choose in §5.

Leakage and skew are the same question asked twice: *what does the model
actually know at the moment it decides?*

---

## 5. The prediction as a product: the operating point

A classifier outputs a probability. A business needs a decision, and the step
between them, the **threshold**, is where the money is.

### 5.1 Price the errors

For the claims model: auto-approve when `p_reject < t`; otherwise an assessor
reviews it.

| Outcome | Cost to Aurora |
|---|---|
| auto-approved, claim was fine | ₹0 |
| auto-approved, claim **should have been rejected** | its amount, mean **₹98,482** |
| sent to an assessor | **₹500** |

That is **197 : 1**. A metric that weighs the two errors equally (accuracy,
F1) is optimising a different business from the one you are in (Elkan).

### 5.2 The table that ends the argument

Holdout, months 12–13, 3,796 claims, the honest model:

| Policy | Threshold | ₹ per claim | Automated | Bad claims paid |
|---|---|---|---|---|
| Review everything (no model) | — | **500** | 0% | 0 |
| Default | 0.5 | **6,451** | 88.3% | 248 |
| F1-optimal | 0.225 | 3,771 | 84.4% | 158 |
| **Cost-optimal** | **0.018** | **466** | **14.0%** | 4 |

- The default threshold costs **12.9× as much as having no model at all**.
- The threshold most people would pick, the F1 maximum, costs an extra
  **₹241 crore a year** at 2,000 claims a day.
- The right threshold automates **14%** of claims and saves **₹2.45 crore a
  year**. That is real, modest, and nothing like the "most of the manual
  queue" the handover implied.

### 5.3 How sure are you?

At the cost-optimal threshold only **4** bad claims are paid on the holdout.
The model's entire margin over "review everything" (₹34 a claim) rests on a
handful of events. Bootstrap the holdout 1,000 times and the cost at 0.018
ranges over **₹435–510 per claim** (95% interval), which straddles ₹500. The
model beats reviewing everything in 95% of resamples. The recommendation
survives, and it has to be stated with that caveat.

### 5.4 The threshold is part of the model

A threshold chosen in a notebook and retyped into a service drifts from the
model it belongs to. Ship them together: in Lab 9 the **bundle** is the model
plus a metadata file holding the feature order, the threshold and the
fingerprint, built by a pipeline stage and read by the service at startup.

---

## 6. Serving: the contract

### 6.1 The schema is the promise

An HTTP service makes one promise to its callers: *this is what I accept, and
this is what you get back.* In FastAPI the promise is a Pydantic class. Types,
allowed values and bounds are checked before your code runs. Choose the
tightest honest type:

- **Categories as `Literal`s, taken from the data.** An unknown plan name
  passed through to a tree model does not crash. It gets a confident,
  meaningless probability.
- **Bounds that admit every real value and reject every typo.** A claim at 3×
  the sum insured is not an outlier; it is a bug upstream.
- **Unknown fields refused, not ignored.** Pydantic ignores extra fields by
  default. A client that sends `assessor_note_length` has misunderstood when
  the model runs; `extra="forbid"` makes that a 422 naming the field on day
  one.

### 6.2 422 is not 500

| Status | Says | A well-built client |
|---|---|---|
| 422 | *your request is wrong* | fixes it; does not retry |
| 500 | *we broke* | retries, with backoff, often automatically |

A malformed request that produces a 500 is retried by every client that has
retry logic. One bad upstream deploy becomes a retry storm. **Malformed input
must never be a 500.** Lab 9's contract suite has ten malformed cases for
this reason.

### 6.3 Liveness is not readiness

| Endpoint | Question | On failure, an orchestrator… |
|---|---|---|
| `/health` | is the process alive? | restarts it |
| `/ready` | can it answer correctly *now*? | stops sending it traffic |

Conflate them and either a slow model load gets the container killed in a
loop, or traffic arrives before the model does. Load the model once, at
startup, and let `/ready` say when it is done. The reference loads its model
in about 0.5 s.

---

## 7. Containers: what an image guarantees

### 7.1 What it is

An image is a **stack of read-only layers**, one per filesystem-changing
instruction, plus metadata (user, command, health check). A container is a
process started from it, with its own filesystem view. Two consequences drive
every Dockerfile decision:

- **Deleting in a later layer does not shrink the image.** The course image's
  first draft ran `chown -R` over its Python environment in a separate layer
  and duplicated every file: **+977 MB**.
- **Layer order is cache order.** Dependencies before code, and a code change
  rebuilds in seconds.

### 7.2 What it guarantees, and what it does not

| Guaranteed | Not guaranteed |
|---|---|
| the same files, libraries and OS userland wherever the image runs | the same **kernel** (it is the host's) |
| the same bits of model output: measured identical on ARM and x86 hosts | the same *image* when rebuilt: timestamps change the digest |
| the dependency versions that were resolved **at build time** | that those were the right ones, unless a lockfile pinned them |
| | performance: the host's CPU and memory are what they are |
| | a GPU on macOS: Docker there has none (it matters in week 4) |

This is why the whole course runs in one Linux image. It turns §2's
"macOS and Linux differ in the last bits" into "every laptop gets the same
bits".

### 7.3 The naive Dockerfile, line by line

```dockerfile
FROM python:3.12            # full image: a compiler toolchain you never run
WORKDIR /app
COPY . .                    # the whole folder: git history, DVC cache, the DATA
RUN pip install fastapi uvicorn scikit-learn pandas joblib pyarrow   # unpinned
CMD ["uvicorn", ...]        # as root
```

Measured, in a team repo: **2.57 GB**, runs as **root**, and `/app` contains
the git history, the DVC cache and **the customers' claims data**.
scikit-learn installs as 1.9.1, which matches the pickle **by luck**: it is
whatever was newest on build day.

### 7.4 The five decisions that fix it

| Decision | Effect |
|---|---|
| `python:3.12-slim` base | no compiler toolchain; wheels need none |
| **multi-stage**: build the environment in stage 1, copy only it into stage 2 | build tools and caches stay behind |
| install from the **lockfile**, serving dependencies only | exact versions; no DVC, MLflow, pytest in production |
| an **allowlist** `.dockerignore` (`*`, then `!` what is needed) | context 320 bytes; fails closed when someone adds a file |
| a **non-root user** and a **HEALTHCHECK** on `/ready` | smaller blast radius; Docker knows when it is actually serving |

Result: **698 MB**, uid 10001, healthy in about 5 s, and **ready to answer 1.3 s
after `docker run`**.

---

## 8. Load, latency and batching

### 8.1 Percentiles, not means

The mean hides the requests users complain about. p95 is the latency one
request in twenty exceeds; for a page that makes twenty calls, it is the
typical worst call on *every* page view (Dean & Barroso, *The Tail at Scale*).
Report p50, p95, p99.

### 8.2 The knee, and Little's law

One uvicorn worker, closed-loop load, measured:

| Concurrent clients | Claims/s | p50 ms | p95 ms |
|---|---|---|---|
| 1 | 60.8 | 14.7 | 29.3 |
| 8 | 81.3 | 96.7 | 114.1 |
| 32 | 114.1 | 279.5 | 331.9 |

Throughput barely moves after the first few clients, while latency grows
roughly in proportion to them. That is the **knee**: past it, more clients
buy only longer queues. **Little's law**, *concurrency = throughput ×
latency*, predicts it exactly: 32 clients ÷ 114 requests/s = 0.28 s, which is
the measured mean.

### 8.3 Batching

Most of a request's cost is **per request** (HTTP, validation, building a
DataFrame, one `predict_proba` call), not per claim. Fifty claims per request:
**2,987 claims/s at p95 74 ms**. That is 26× the saturated single-request
throughput *and* a lower p95. Batch wherever the caller can wait for a batch.

### 8.4 Size to the workload first

Aurora files 2,000 claims a day: **0.023 claims per second**. The simplest
single-process service clears a whole day's volume, one claim at a time, in
about **33 seconds**. Before you add workers, replicas or a GPU, write down
the real workload. Most performance work on most models is not needed, and
the effort belongs elsewhere: in this case, in the threshold of §5, which is
worth crores.

---

## 9. Labs 8–9 briefing

- **Lab 8 — The model is not the system.** Rebuild the supplied model and
  measure how much it disagrees with itself. Find the leak with evidence and
  the timing argument. Make training bit-identical across runs, threads, row
  order, a clean clone and a teammate's laptop, with DVC and MLflow. Choose
  the operating point in rupees.
- **Lab 9 — Serve it, contain it.** Built by hand, no coding agents. A FastAPI
  service whose contract refuses what it should (15 tests, ten of them
  malformed input). Measure the naive Dockerfile, write a slim one, run it,
  cold-start it, load it, and have a teammate rebuild it and serve the same
  model.

---

## Reading

- Sculley et al. (2015), *Hidden Technical Debt in Machine Learning Systems*,
  NeurIPS. The diagram in §1. Read it all; it is short.
- Breck et al. (2017), *The ML Test Score: A Rubric for ML Production Readiness
  and Technical Debt Reduction*, IEEE Big Data. A checklist to hold Labs 8–13
  against.
- Kaufman, Rosset, Perlich & Stitelman (2012), *Leakage in Data Mining:
  Formulation, Detection, and Avoidance*, ACM TKDD. §2–3.
- Elkan (2001), *The Foundations of Cost-Sensitive Learning*, IJCAI. Why the
  threshold follows from the cost matrix.
- Dean & Barroso (2013), *The Tail at Scale*, Communications of the ACM.
- scikit-learn documentation: `HistGradientBoostingClassifier`, parameters
  `early_stopping`, `validation_fraction`, `random_state`.
- DVC documentation: *Get Started: Data Pipelines*, and the `dvc.yaml`
  reference. MLflow documentation: *Tracking*.
- Docker documentation: *Multi-stage builds* and *Building best practices*.
  Kubernetes documentation: *Configure Liveness, Readiness and Startup
  Probes*.

## Check yourself

1. A colleague says their model is "reproducible" because two runs gave AUC
   0.9218 both times. Which level is that, and what would you ask for?
2. You set `random_state` and still get different models from the same data.
   Name two causes, and the experiment that tells them apart.
3. Why does a model that is bit-identical in a Linux container differ in the
   17th decimal place on a Mac, with every package pinned? Why does it not
   differ between ARM and x86 Linux?
4. A feature has permutation importance 0.43 AUC. Is it a leak? What single
   question decides it?
5. Errors cost ₹500 and ₹98,000. Without any data, which way does the
   cost-optimal threshold move from 0.5, and why?
6. Your service returns 500 on a request with a misspelled plan name. Describe
   what happens next in a system whose clients retry.
7. `docker run` → `/ready` takes 1.3 s. Where do those 1.3 seconds go, and
   which part would you attack first if it were 30 s?
8. At 32 concurrent clients, throughput is 114 requests/s. Use Little's law to
   predict the mean latency, then say what adding more clients will do.
