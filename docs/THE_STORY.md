# The story of the course

*AI in Practice 2, Labs 8–21, as one story. Read it once at the start, and again
whenever you wonder why this week's lab exists.*

---

## You

You work in **Platform Engineering at Aurora Health**, the Indian health insurer
whose policy assistant and ticket extractor you built in Module 1. Platform
Engineering takes what other teams build and makes it something the company can
run: rebuilt from scratch on demand, served, shipped, watched, and trusted.

Over eight weeks one question gets harder: **can somebody else run this, own
it, and trust it?** First for a model your colleagues hand you, then for a stack
that must never touch the internet, then for an agent that takes actions, and
finally for a system you build for a client who is not you.

## The four arcs

| Arc | Labs | The question | Who is asking |
|---|---|---|---|
| **A · Ship it** | 8–13 | Can a stranger clone it, run it, deploy it and watch it? | Aurora's claims operations |
| **B · Own it** | 14–15 | Can it run with the network cable pulled? | another insurer, a prospective client |
| **C · Let it act** | 16–18 | Can it take actions safely, and can you prove it? | a partner from another industry |
| **D · Deliver it** | 19–21 | Can a team take a client's problem to a handover? | your capstone client |

---

## Arc A · Ship it: one model, all the way to production and back

### Lab 8 · The model is not the system
Aurora's data-science team hands you a claims-triage model with a note: *trained
and tested, ready for production, please deploy.* The card says accuracy 0.981.
You find that it cannot be rebuilt the same way twice, that one column was
written **after** the decision it predicts, and that the honest model, about
0.92 AUC, should automate 14% of claims, not the ~88% the card implied. You make
it reproducible from a clean clone (git, DVC, MLflow) and put its threshold in
rupees.
**Hands forward:** the pipeline, `params.yaml`, the operating point.
> *If you cannot rebuild it, you do not know what you deployed.*

### Lab 9 · Serve it, contain it
The claims system wants to send a claim over HTTP and get a decision back, and
Platform Engineering's rule is that anything shipped is an image someone else
can build and trust. You write the contract (the leak column is refused at the
door), a slim non-root image, and measure what it costs to start and how much
it can take. You keep a time log of doing it by hand.
**Hands forward:** the service, the image, the bundle, and the time log.
> *A service is a promise about what it accepts, how fast it answers, and which model it is running.*

### Lab 10 · Build it with an agent
Coding agents arrive. You redo part of Lab 9 with one and compare against your
time log, then build a new service the way a professional uses an agent: spec
and failing tests first, the agent second, every diff reviewed. The new service
answers Fraud and Triage's question, *what has this policy claimed?*, over 365
days.
**Hands forward:** the way you work with agents from here on, and the habit of
writing the definition before the code.
> *The agent writes the code. You own what it means.*

### Lab 11 · The skew
The claims system is about to stop sending one feature, the number of claims in
the last 90 days, and the service must compute it. That is the same kind of
question Lab 10's service answered, with a different window and boundary rule,
and you discover the training data's version was computed differently again.
The model was trained on one definition and would be served another. You measure
the damage in rupees, make one definition shared by training and serving,
retrain, and restate the business case: now 6.6% automated, beating "review
everything" in only 59.5% of resamples.
**Hands forward:** `features.py`, the retrained model, tests that keep the skew out.
> *One feature, one definition, one place in the code, and a test that proves it.*

### Lab 12 · Ship it continuously
Aurora wants releases as often as you improve the model, but will not trust a
process that depends on someone remembering the checks. One team laptop becomes
"production". You build the pipeline every change goes through: rebuild the
model, test, gate on the evaluation, build the image, release to a canary judged
against a baseline, and roll back in seconds. The gate passes the retrained
model by ₹2 a claim. Remember that number.
**Hands forward:** the production laptop, the pipeline, the gate.
> *A pipeline earns trust by failing, a canary by being judged against the right thing, and a rollback by being timed before it is needed.*

### Lab 13 · Operate it
Fast-forward a year. You replay twelve months of claims through what you
shipped, with tracing, dashboards and monitors for drift, calibration, cost and
subgroups. A policy rule changes in month 14, Hinglish claims are caught less
often than English ones, and in production the model costs about ₹575 a claim
against ₹500 for reviewing everything. The honest answer is to switch the
automation off, and to say so in a note a claims manager would read.
**Hands forward:** the habit of asking how you would know it stopped working.
> *A dashboard tells you the service is up. Only outcomes tell you the model is right, and they come late.*

**How Arc A ends.** Aurora takes your advice: every claim is reviewed, and the
model only puts the review queue in order. The business case shrank at every
honest step (about 88% implied, then 14%, then 6.6%, then a loss), and finding
that out cheaply is what the engineering was for.

---

## Arc B · Own it: the same AI, with nothing leaving the building

### Lab 14 · Go local
The AI Aurora sells is the other half of its platform, the half you built in
Module 1. A prospective client, an insurer that may not send customer data
abroad, asks whether the ticket extractor could run on its own machines, and
many of its customers write in Hinglish. You keep your Module 1 harness and
change the model: open models on your own laptop, measured for quality, speed
and memory, against the API.
**Hands forward:** your local model choice, used in Labs 15–18.
> *A local model is a measurement, not a download.*

### Lab 15 · The air-gapped stack
The client liked the numbers and adds a condition: *show us the policy assistant
answering our staff with nothing leaving the machine, prove it, and tell us what
we lose.* You run the whole Aurora service sealed, with one logged door, try to
break the seal, and measure the quality you give up. The log catches a library
phoning home, and a model that leaves through the one door that was allowed.
**Hands forward:** the sealed-stack pattern most capstones need.
> *"Nothing leaves" is a claim you prove with a log, and it covers everything on the machine.*

---

## Arc C · Let it act: a partner's systems, an agent, and an attacker

In January your partner will not be an insurer you know. From Lab 16 each team
takes one partner's systems, a **pack**: insurance, healthcare, legal, finance
or agritech, and works for that partner for three labs.

### Lab 16 · Tools as a standard
The partner wants an assistant on its systems, and its platform team asks first
for the tools, in a form they can review and test. You publish them as an MCP
server, mark honestly which ones change anything, and prove the contract from a
client you did not write.
**Hands forward:** your `server.py`, which Labs 17 and 18 run.
> *A tool is what the client receives: its description, its errors, and whether it changes anything.*

### Lab 17 · The domain agent
The operations lead: *put an assistant on it, but nothing gets referred,
flagged, matched or sent without one of my people saying yes.* You build the
agent loop by hand, then with an SDK, with a human at the gate, and measure it
the way agents must be measured: five runs, two models, success, cost and
variance. You will find an agent that records an action its own answer says it
did not take.
**Hands forward:** your agent loop, and your pack's baseline numbers.
> *An agent is three numbers, not one run. The ledger is the truth.*

### Lab 18 · Trust the agent
The security team will not sign off: *show us how it behaves when the data is
hostile and a tool lies, on a model we can run here.* You read the agent's real
trajectory from the server's trace, attack it through its tools, and defend the
**action** with a policy gate in code. Most attacks are stopped; you report the
one you could not stop.
**Hands forward:** the red-team habit every capstone must show.
> *Attack it through its tools, defend the action rather than the prompt, and keep the failure you could not fix.*

---

## Arc D · Deliver it: a client, a scope, a demo, a handover

### Lab 19 · Capstone kickoff
Your team gets a client brief, usually continuing your pack or one of the
earlier arcs, written the way a partner writes: a sentence or two, and not the
real problem. You interview the client, re-measure the brief's baseline, and
leave with a signed one-page scope.
> *The ask is not the requirement. The requirement is the page the client signed.*

### Lab 20 · Sprint review
The client sees it run for the first time: from a clean clone, with a gate you
break in front of them. Then they ask for a change, as clients do, and you
answer with a price.
> *A slice is real when it runs from a clean clone and its gate fails on cue.*

### Lab 21 · Demo Day and handover
Eight minutes, live, to a panel that has never seen your system, including what
you would not deploy it for. Then the handover pack: a runbook, decision
records, on-call notes, the evaluation report and its limitations.
> *Leave it so someone who has never met you can run it tomorrow, and knows what it must not be used for.*

---

## What carries forward

| You build | In | Used again in |
|---|---|---|
| a reproducible pipeline (`dvc.yaml`, `params.yaml`) | Lab 8 | 9, 11, 12 (CI rebuilds it on every push) |
| the service and its image | Lab 9 | 11 (v2), 13 (v3), 12 (CI builds it) |
| your way of working with coding agents | Lab 10 | every lab after it |
| `features.py` and the retrained model | Lab 11 | 12, 13; the insurance pack's scores |
| the pipeline, the gate, the production laptop | Lab 12 | 13; the capstone's CI and gate |
| monitors and the "how would we know" question | Lab 13 | capstone Brief 6; every capstone's limitations |
| your Module 1 harness | Module 1 | 14; capstone Brief 7 |
| your local model choice | Lab 14 | 15–18 |
| the sealed stack | Lab 15 | capstone Brief 8; Lab 18's stretch |
| your MCP server | Lab 16 | 17, 18; capstone Briefs 1–5 |
| your agent loop and its numbers | Lab 17 | 18; the baselines of Briefs 1–5 |
| your policy gate and red team | Lab 18 | every capstone |

Keep every lab working and tagged: the next one starts from it.

## The ideas that run through all of it

- **No number, no claim.** Every rubric, every lab. Honest negative results
  score full marks; fabricated ones score zero.
- **Somebody else can run it.** The clean clone in Lab 8 becomes CI in Lab 12
  and the clean-clone rehearsal before Demo Day.
- **A check is proven only by watching it fail.** Red tests first (Lab 10), a
  skew guard shown failing (11), four red builds (12), a seal you try to break
  (15), a gate broken on purpose (20).
- **Read the evidence, not the summary.** The diff, not the agent's summary
  (10); the ledger, not the agent's answer (17); the trace, not its log (18).
- **Rupees, not accuracy.** Every decision is priced in what a mistake costs the
  business.
- **Humans at the gate, rules in code.** What must never happen is enforced in
  code, not asked for in a prompt (17, 18, the capstone).
- **Nothing leaves, proven.** A claim about data is checked with a log (15).
- **Look at subgroups.** Hinglish claims (13), Hinglish tickets (14), Hindi
  advisories (agritech): the average hides who is failing.

## The tools, and where to learn them

Each lab uses tools that no earlier course taught you from zero: git with a team,
DVC, MLflow, Docker, make, pytest, GitHub Actions, Ollama, MCP. The
[toolkit](toolkit/README.md) has a short primer for each, with the commands this
course actually uses, and says which lab needs it first.
