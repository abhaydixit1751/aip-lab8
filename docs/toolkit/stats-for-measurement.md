# Toolkit — statistics for measurement

**Who needs this.** Every lab that reports a number: Labs 9 and 12–13
(percentiles), 11 (bootstrap), 12 (gate headroom, canary noise), 13 (PSI, KS),
14–15 (standard error, sign test), 17–18 (pass^k) and the capstone report.

**Measured with** Python 3.12.14, numpy 2.5.3 and scipy 1.18.1 in the course
container: every snippet was run there, and the outputs are real.

> **The minimum.**
> - Report latency as **p50 / p95 / p99**, never as a mean.
> - A proportion from `n` items has standard error `√(p(1 − p)/n)`. A difference
>   smaller than that is not established.
> - Same items, two systems? Count wins and losses, ignore ties, and run the
>   **sign test** (the 3-line function in §4). 1 against 8 gives p = 0.039.
> - Before writing any threshold, run the unchanged system several times: the
>   spread is the **noise floor**, and the threshold must sit outside it.
> - For agents, report the mean, the spread across runs, and **pass^k**.

---

## 1 · Percentiles, and why means mislead

**Definition.** The p95 is the value 95% of observations are at or below. p50 is
the median. **Where:** Labs 9 and 11 (`load.py` prints p50/p95/p99), Lab 12
(canary p95 vs baseline), Lab 13 (SLO: p95 ≤ 50 ms).

```python
import numpy as np
lat = np.array([10] * 98 + [1000] * 2)            # ms: 98 fast requests, 2 stuck ones
print(lat.mean(), np.percentile(lat, [50, 95, 99]))
```

```
29.8 [  10.   10. 1000.]
```

The mean, 29.8 ms, describes no request that happened: three times the
typical one, and far from the two users who waited a second. Latency is
skewed, and the tail is where users complain, so report p50 (typical), p95 and
p99 (the tail), with `n`. A p99 from 100 requests rests on one or two of them;
say so. Prometheus's `histogram_quantile` (Lab 13) estimates percentiles by
interpolating inside buckets, so it is only as fine as the bucket edges.

## 2 · Standard error

**Definition.** How much a number computed from a sample would move if you drew
another sample of the same size. **Where:** Lab 12 (gate bounds: about one
standard error of headroom), Lab 14 (is a model difference bigger than noise?).

    proportion:  SE = √(p(1 − p) / n)          mean:  SE = s / √n   (s = sample standard deviation)

```python
from math import sqrt
import numpy as np
p, n = 0.46, 120
print(round(sqrt(p * (1 - p) / n), 4), round(sqrt(p * (1 - p) / 17), 3))
x = np.array([12.1, 11.8, 12.6, 13.0, 11.9])       # five runs of one measurement
print(x.mean(), round(x.std(ddof=1) / sqrt(len(x)), 3))
```

```
0.0455 0.121
12.28 0.227
```

Lab 14's numbers: record accuracy 0.46 on 120 tickets has SE 0.045, so a
3-point gap between two models is inside one SE; on the 17 Hinglish tickets the
SE is 0.12, and almost nothing is established. About ±2 SE is a rough 95%
interval. A gate bound set right at the measured value fails on noise; one SE
below it (Lab 12) does not.

## 3 · The bootstrap confidence interval

**Definition.** When there is no simple formula (a cost per claim at a fixed
threshold, a median), resample the data **with replacement**, `n` from `n`,
recompute the number each time, and take the middle 95% of the results.
**Where:** Lab 11 (`labs/lab11/bootstrap.py`), Lab 8 stretch 3.

```python
import numpy as np
rng = np.random.default_rng(0)
data = rng.exponential(20, size=200)                # 200 skewed values
boots = [rng.choice(data, data.size).mean() for _ in range(1000)]
print(data.mean().round(2), np.percentile(boots, [2.5, 97.5]).round(2))
```

```
22.58 [19.92 25.45]
```

`bootstrap.py` does exactly this to the Lab 8 holdout (3,796 claims): 1,000
resamples of row indices with a fixed seed (`rng.integers(0, n, n)`), the cost
per claim recomputed **at the threshold you chose once** (re-choosing it on each
resample would be optimistic), then the 2.5th and 97.5th percentiles. Measured:

```
threshold 0.018   holdout n = 3,796   bad claims paid 4   automated 14.0%
Rs/claim 466   95% interval Rs 435 - 510   (1,000 resamples)
beats reviewing everything (Rs 500) in 95.0% of resamples
```

The interval crosses ₹500: the model beats reviewing everything in 95% of
resamples, not always. That sentence, not "₹466", is the honest result.

## 4 · The sign test (paired comparison)

**Definition.** Two systems answer the **same** items. Count the items where A
scored higher (wins) and where B did (losses); drop ties. If neither is better,
each untied item is a fair coin flip, so the number of wins is
Binomial(n = wins + losses, ½). The two-sided p-value is the chance of a split
at least this lopsided:

    p = min(1, 2 × Σ_{i=0}^{k} C(n, i) / 2ⁿ)        k = min(wins, losses)

**Where:** Lab 14 (ticket by ticket), Lab 15 C3 (question by question), Lab 17
Part D and Lab 18 (task by task). Pairing removes the difficulty of each item
from the comparison, which is why it can see differences a standard error
cannot.

```python
from math import comb
def sign_test(wins, losses):
    n, k = wins + losses, min(wins, losses)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)
for w, l in [(1, 8), (3, 4), (14, 9), (31, 2)]:
    print(w, l, f"{sign_test(w, l):.2g}")
```

```
1 8 0.039
3 4 1
14 9 0.4
31 2 1.3e-07
```

Lab 15's reference: the sealed stack was worse on 8 questions, better on 1, tied
on 31: p = 2 × (C(9,0) + C(9,1)) / 2⁹ = 20/512 = **0.039**. Lab 17's: the API
model beat the local one on 31 tasks and lost on 2, p ≈ 1.3 × 10⁻⁷. Lab 14's
"14 to 9" example is p = 0.4: a coin-flip-sized difference.

scipy is in the course image and agrees: `from scipy.stats import binomtest;
binomtest(1, 9).pvalue` → `0.0390625`. **McNemar's test** is not used in the
course; for paired pass/fail outcomes its exact form is this same calculation on
the discordant pairs, so the function above covers it.

## 5 · PSI and KS: has a distribution moved? (Lab 13)

**PSI** (Population Stability Index) compares the share of a reference and of a
current period in each bin:

    PSI = Σ over bins (a − e) · ln(a / e)          e, a = reference, current share in the bin

Categorical columns: one bin per value; numeric: deciles of the reference. Floor
empty shares at 1e-4 so `ln` never sees zero. Rule of thumb: < 0.1 stable,
0.1–0.25 watch, > 0.25 act, set for credit scorecards, not for your features.
Given the shares (the binning is your Lab 13 C1):

```python
import numpy as np
e, a = np.array([0.5, 0.3, 0.2]), np.array([0.2, 0.3, 0.5])
print(round(float(np.sum((a - e) * np.log(a / e))), 3))
```

```
0.55
```

Lab 13 measured `channel` at 0.76 with no change in reject rates: loud, unimportant.

**KS** (two-sample Kolmogorov–Smirnov) compares two samples of a numeric
feature through their cumulative distributions: `D = max over x of |F_ref(x) −
F_cur(x)|`, the largest vertical gap, from 0 (identical) to 1. It needs no bins.

```python
import numpy as np
from scipy.stats import ks_2samp
rng = np.random.default_rng(0)
r = ks_2samp(rng.normal(0, 1, 1000), rng.normal(0.2, 1, 1000))
print(round(r.statistic, 3), f"{r.pvalue:.1g}")
```

```
0.129 1e-07
```

A shift of a fifth of a standard deviation gives a small D and a tiny p-value
at n = 1,000. On production volumes almost every feature "drifts significantly";
read D (the size), not p, and ask whether the model's output moved.

## 6 · pass^k and flaky tasks (Lab 17)

**Definitions.** Run every task `k` times. **pass@1** is the mean success rate.
**pass^k** is the share of tasks that passed **all** `k` times. A task is
**flaky** if it passed some runs but not all (0 < passes < k).

```python
import numpy as np
k, passes = 5, np.array([5, 5, 4, 3, 0])            # passes out of 5, per task
print(round(passes.mean() / k, 2), (passes == k).mean(), int(((passes > 0) & (passes < k)).sum()), round(0.8**5, 3))
```

```
0.68 0.4 2 0.328
```

pass@1 says 0.68; only 40% of tasks work every time. A task that passes with
probability 0.8 passes five runs in a row only a third of the time (0.8⁵), and
a partner who uses it daily meets the failure weekly. Lab 17's reference: the
local agent's pass@1 was 0.512, its pass^5 **13 of 50**; the API agent's 0.860
and **40 of 50**. Report both, plus the spread of the per-run rates (local: 0.42
to 0.58).

## 7 · The noise floor (Lab 12, and every comparison)

**Definition.** Run the unchanged system several times and look at the spread
of the number you plan to judge by. Any rule tighter than that spread fires on
noise. **Where:** Lab 12's canary (same image as canary and baseline), Lab 14's
repeated speed runs, Lab 17's five runs.

```python
import numpy as np
ratios = np.array([0.6, 0.8, 0.9, 1.0, 1.0, 1.2, 2.3])   # canary p95 / baseline p95, illustrative
print(np.percentile(ratios, [0, 50, 100]), ratios.std(ddof=1).round(2))
```

```
[0.6 1.  2.3] 0.56
```

Lab 12's reference, 12 runs with nothing different: canary/baseline p95 ranged
0.60 · 0.99 · 2.31 (min, median, max). A rule of "canary p95 > 1.5 × baseline"
would have rolled back good releases. The reference chose `> 2 × baseline +
5 ms`: it flagged 0 of 12 identical releases and caught the slow image (2.3–5.3×)
in 11 of 12. Compared with the long-running *stable* pool instead of a fresh
baseline, the same rule caught it in 1 of 12. The noise floor depends on what
you compare with as much as on the rule.

---

## If it goes wrong

| Symptom | Cause and fix |
|---|---|
| A "better" model loses on the next run | The gap was inside the noise: SE (§2) or the sign test (§4) first |
| p95 jumps around between runs | Too few requests per run: p95 of 40 rests on 2. More requests, or report the range |
| Sign test p = 1 with clear wins | Too few untied items: 3 to 0 gives p = 0.25. More items |
| PSI is `inf` or `nan` | An empty bin: floor shares at 1e-4 |
| KS p-value 0.0000 on a harmless change | Large n: read D instead |
| Canary rolls back identical releases | Rule tighter than the noise floor, or compared with stable not baseline |
| Bootstrap interval suspiciously narrow | You resampled something already averaged, or re-tuned the threshold inside each resample |
