#!/usr/bin/env python3
"""Lab 8, Part D -- where should the threshold sit?  Answered in rupees, not F1.

    python labs/lab08/operating_point.py          # reads artifacts/lab08/predictions.parquet

The business process being modelled (DATA_CARD.md, "Business context"):

    p_reject <  t   ->  auto-approve. If the claim should have been rejected,
                        Aurora pays it out:            cost = claim_amount
    p_reject >= t   ->  an assessor reviews it and decides correctly:
                                                       cost = Rs 500

Evaluated on the holdout (months 12-13) only -- never on training months.
Writes artifacts/lab08/operating_point.json.

Layout: provided above the `YOURS` banner; two functions below it are yours.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score


def find_root(start: Path) -> Path:
    for d in (start, *start.parents):
        if (d / "pyproject.toml").exists():
            return d
    raise FileNotFoundError(f"no pyproject.toml above {start}")


ROOT = find_root(Path(__file__).resolve().parent)
REVIEW_COST = 500          # Rs per manual review
CLAIMS_PER_DAY = 2_000
GRID = np.unique(np.concatenate([np.linspace(0.001, 0.999, 999), [0.5]]))   # thresholds tried


def load_holdout() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(p_reject, y, claim_amount) for the holdout, aligned by claim_id."""
    claims = pd.read_parquet(ROOT / "data/claims/claims.parquet")
    preds = pd.read_parquet(ROOT / "artifacts/lab08/predictions.parquet")
    hold = claims[claims["month_index"].between(12, 13)].merge(preds, on="claim_id", how="left")
    if hold["p_reject"].isna().any():
        raise SystemExit("predictions.parquet is missing holdout claims -- rerun train.py")
    hold = hold.sort_values("claim_id")
    return (hold["p_reject"].to_numpy(), hold["rejected"].to_numpy().astype(int),
            hold["claim_amount"].to_numpy())


def describe(t: float, p: np.ndarray, y: np.ndarray, amount: np.ndarray) -> dict:
    auto = p < t
    total = cost_at(t, p, y, amount)
    return {
        "threshold": round(float(t), 3),
        "cost_inr": total,
        "cost_per_claim_inr": total / len(y),
        "automation_rate": float(auto.mean()),
        "bad_claims_paid": int((auto & (y == 1)).sum()),
        "reviews": int((~auto).sum()),
        "f1": float(f1_score(y, ~auto, zero_division=0)),
    }


def main() -> None:
    p, y, amount = load_holdout()
    n = len(y)
    t_cost, t_f1 = choose_thresholds(p, y, amount)

    policies = {
        "review_everything": {"cost_per_claim_inr": float(REVIEW_COST), "automation_rate": 0.0},
        "approve_everything": {"cost_per_claim_inr": float(amount[y == 1].sum()) / n,
                               "automation_rate": 1.0},
        "default_0.5": describe(0.5, p, y, amount),
        "f1_optimal": describe(t_f1, p, y, amount),
        "cost_optimal": describe(t_cost, p, y, amount),
    }
    best = policies["cost_optimal"]["cost_per_claim_inr"]
    per_year = CLAIMS_PER_DAY * 365
    out = {
        "n_holdout": n,
        "reject_rate": float(y.mean()),
        "policies": policies,
        "annual_saving_vs_review_everything_inr": (REVIEW_COST - best) * per_year,
        "annual_extra_cost_f1_vs_cost_optimal_inr":
            (policies["f1_optimal"]["cost_per_claim_inr"] - best) * per_year,
    }
    (ROOT / "artifacts/lab08/operating_point.json").write_text(json.dumps(out, indent=2))

    print(f"holdout n = {n:,}   reject rate {y.mean():.3f}\n")
    print(f"{'policy':<20}{'thr':>7}{'Rs/claim':>10}{'auto %':>9}{'bad paid':>10}{'reviews':>9}{'F1':>7}")
    for k, v in policies.items():
        f1 = f"{v['f1']:.3f}" if "f1" in v else ""
        print(f"{k:<20}{v.get('threshold', ''):>7}{v['cost_per_claim_inr']:>10.0f}"
              f"{100 * v['automation_rate']:>8.1f}%{v.get('bad_claims_paid', ''):>10}"
              f"{v.get('reviews', ''):>9}{f1:>7}")
    crore = 1e7
    print(f"\nAt {CLAIMS_PER_DAY:,} claims/day the cost-optimal threshold saves "
          f"Rs {out['annual_saving_vs_review_everything_inr'] / crore:.2f} crore/yr vs reviewing everything.")
    print(f"The F1-optimal threshold costs an extra "
          f"Rs {out['annual_extra_cost_f1_vs_cost_optimal_inr'] / crore:.0f} crore/yr.")
    print(f"The default 0.5 threshold costs {policies['default_0.5']['cost_per_claim_inr'] / REVIEW_COST:.1f}x "
          f"as much as having no model at all.")


# ════════════════════════════════════════════════════════════════════════════
#  YOURS
# ════════════════════════════════════════════════════════════════════════════

def cost_at(t: float, p: np.ndarray, y: np.ndarray, amount: np.ndarray) -> float:
    """Total rupees Aurora spends on these claims if it auto-approves p < t.

    Two terms, from the docstring at the top of this file. y == 1 means the
    claim should have been rejected. Return a plain float.
    """
    raise NotImplementedError("Part D -- see CONCEPTS.md, 'The operating point'")


def choose_thresholds(p: np.ndarray, y: np.ndarray, amount: np.ndarray) -> tuple[float, float]:
    """Return (cost-optimal threshold, F1-optimal threshold), each chosen from GRID.

    F1 here treats "sent to review" (p >= t) as the positive prediction.
    """
    raise NotImplementedError("Part D -- see CONCEPTS.md, 'The operating point'")


if __name__ == "__main__":
    main()
