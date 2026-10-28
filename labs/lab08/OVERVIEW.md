# Lab 8 — The Model Is Not the System
### Note for students · read before the lab

> **In one line.** The data-science team handed over a model with AUC 0.997 and
> a note saying "please deploy". It cannot be rebuilt, it is cheating, and at
> its default threshold it costs Aurora more than having no model at all. You
> find out all three with numbers.

> **Working through the lab?** [`CONCEPTS.md`](CONCEPTS.md) is the reference to
> keep open beside your editor: every concept the lab uses, what it is, where
> it sits in the code, and where it came from in T5.

---

## Why this lab exists

In Module 1 you built things and measured them. That was hard enough. This
course starts from a different question: **can somebody else run what you
built, and get the same answer?** In industry, that "somebody else" is a
colleague, a CI server, an auditor, or you in six months.

The supplied claims model in `supplied_model/` is a very ordinary handover: a
training script exported from a notebook, an unpinned `requirements.txt`, a
pickle, and a confident note. Nothing about it is unusual, and that is why it
makes a good first case. Run the unchanged script three times and you get
three different models. Between any two builds, **roughly 240 to 300 of 45,365 claims
get a different decision**. At 2,000 claims a day that is about a dozen real
customers daily whose claim outcome depends on which build was deployed. Nobody
changed anything to cause that.

Then the headline numbers. AUC 0.997 is not a triumph. It is a symptom, and
you will trace it to one column whose value is **written after the decision
the model is supposed to make**. Remove it and the model is honest and
unremarkable: AUC ≈ 0.92.

Then the part most ML courses never reach. A model that predicts well is not
yet useful: somebody has to choose a threshold, and **each kind of mistake
costs a different amount**. Wrongly auto-approving a claim that should be
rejected costs Aurora its full amount, about ₹98,000 on average. Sending a good
claim to an assessor costs ₹500. That is 197 to 1. Once you put rupees on the
curve, the threshold that maximises F1 turns out to cost Aurora about
**₹241 crore a year** more than the right one.

**Where it sits.** Everything after this lab builds on the model you make
reproducible today. Lab 9 serves it, Lab 11 finds a subtler flaw in one of its
features, and Lab 13 watches it degrade in production. If your model is not
reproducible, none of those later measurements can be trusted.

---

## What you will build

- A **measurement of the problem**: the supplied script rebuilt several times,
  and how much it disagrees with itself and with the pickle you were given
- **Evidence for the leak**: which feature the model depends on, and why that
  feature cannot exist at decision time
- A **reproducible training pipeline**: `train.py` driven entirely by
  `params.yaml`, whose output is fingerprinted and **bit-identical** across runs,
  thread counts, a shuffled copy of the data, and your teammates' laptops
- **Versioning for all four parts of the artefact**: code in git, data and
  model in DVC, experiments in MLflow, environment in the course container, and
  a **clean clone that rebuilds the identical model** from nothing
- An **operating point in rupees**: the cost-optimal threshold, what it saves,
  what the F1-optimal threshold would have cost, and how much of the claims
  queue the honest model really automates

---

## How to approach it

**Measure before you fix.** Parts A and B are deliberately in that order.
Part A tells you *how much* the model disagrees with itself and *which*
feature it leans on. Part B is where you fix things. A team that starts editing
`train.py` in minute five will not know which of its changes mattered.

**Make "the same model" a yes/no question.** Two models that "look about the
same" are not a result. `train.py` writes a SHA-256 fingerprint of every
predicted probability, and `check_reproducible.py` compares two runs and
answers at one of three levels: **bit-identical**, **decision-identical**, or
**different**. Use those words in your report, and say which level you are
claiming.

**Test the trap before you fix it.** Textbooks list many ways a model can fail
to reproduce. On this model, with these library versions, some of them are
real and some measure as exactly zero. Your report should say which is which
and give the evidence. An honest "we tested it and it made no difference" gets
full credit. A fix nobody showed was needed does not.

**Work as three.** One person drives, one navigates (reads the runsheet and
says what comes next), one is the **skeptic**: they read every number aloud,
ask "compared to what?", and keep the notes. Rotate roles at every part.

---

## Where this comes from in the theory

| Theory | What it claimed | Where you meet it today |
|---|---|---|
| **T5 §1** — the artefact problem | A model is code + data + weights + environment; usually three are unversioned | Part A. Count what the handover left unversioned |
| **T5 §2** — reproducibility is testable | "Same model" needs a definition and a check; three levels | Part B. Your fingerprint, and the three words you report |
| **T5 §2.2** — where nondeterminism hides | Seeds, data order, threads, platform | Part B. Which of those bite *this* model, measured |
| **T5 §3** — versioning code, data, experiments | git for code, DVC for data and models, MLflow for runs | Part C. The clean clone is the test |
| **T5 §4** — what the model may know | A feature must exist at decision time | Part A. The leak |
| **T5 §5** — the prediction as a product | The threshold is a business decision; price the errors | Part D. The operating point in rupees |
| **T5 §7** — what a container guarantees | Same image, same bits, measured on ARM and x86. Outside it, macOS and Linux differ in the last bits | Setup and the stretch. Why this course runs in one container |

---

## Hints

- **The shipped `model.pkl` cannot be rebuilt either.** In the reference run,
  a rebuild that stopped at exactly the same iteration count as the pickle
  still disagreed with it on 282 claims. Ask what the handover would have
  needed to include for you to rebuild it exactly.
- **The model card tells you where the leak is.** Read its "Features" section
  with one question in mind: *when does this value come into existence?*
- **A seed is necessary and not sufficient.** Seed the model, then feed it the
  same rows in a different order, and see what happens. `load_data()`'s
  docstring tells you how to test this.
- **If check_reproducible says CANNOT COMPARE, it is not being fussy.** It
  refuses missing files, empty fingerprints, and a `metrics.json` that does not
  match the predictions beside it. The first version of this check passed on
  two empty fingerprints, because two empty strings are equal.
- **There are two legitimate fixes for the early-stopping randomness.** Both are
  reproducible. They do not cost the same. If you have time, try the other one
  and put it through Part D.
- **`dvc push` goes after `dvc repro`, not before.** Otherwise the model
  outputs never reach the remote and the clean clone's `dvc pull` fails.
- **The cost-optimal threshold rests on very few claims.** Look at how many
  bad claims are actually paid at that threshold. Then say how confident you
  are in the ₹/claim figure, and why.

---

## What separates a good report from an adequate one

- An adequate report says the pipeline is reproducible. A good one says **at
  which level, under which changes** (runs, threads, row order, a clean clone,
  a teammate's laptop), and shows the checker's output for each.
- An adequate report removes the leak. A good one shows the **evidence**
  (permutation importance) *and* the **timing argument**. Either alone is not
  enough.
- An adequate report picks the cost-optimal threshold. A good one states what
  it **automates**, what it **saves** against reviewing everything, what F1
  would have cost, **and how fragile the estimate is**.
- A good report contains at least one honest negative result, for example a
  suspected source of nondeterminism that measured zero.

---

## Questions we will discuss

1. The supplied model scores AUC 0.997 and the honest one 0.92. Which number
   would you put in front of Aurora's CFO, and what would you say about the
   other one?
2. Your model is bit-identical in the container, but on a Mac outside it 58
   probabilities differ in the 17th decimal place and no decision changes. Is
   that "reproducible"? Who gets to decide?
3. The cost-optimal model automates only 14% of claims. The model card
   implied ~88%. Is this model worth deploying? What would change your answer?
4. What else in Aurora's pipeline might be written *after* the decision it is
   used to predict? How would you find out before a model does?
