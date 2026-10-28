#!/usr/bin/env python3
"""Lab 8, Part A -- what is the supplied model actually leaning on?

    python labs/lab08/inspect_supplied.py

Scores the shipped `supplied_model/model.pkl` on the holdout (months 12-13),
reports the numbers the model card claims, and then asks which features the
model's AUC depends on. One function is yours: `importance()`.

Layout: provided above the `YOURS` banner, yours below. See CONCEPTS.md,
"Permutation importance" and "Leakage".
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score


def find_root(start: Path) -> Path:
    for d in (start, *start.parents):
        if (d / "pyproject.toml").exists():
            return d
    raise FileNotFoundError(f"no pyproject.toml above {start}")


ROOT = find_root(Path(__file__).resolve().parent)


def supplied_features(model, rows: pd.DataFrame) -> pd.DataFrame:
    """Prepare rows exactly the way supplied_model/train_model.py's prep() does."""
    X = rows[list(model.feature_names_in_)].copy()
    for c in X.columns:
        if X[c].dtype == bool:
            X[c] = X[c].astype(int)
        elif not pd.api.types.is_numeric_dtype(X[c]):
            X[c] = X[c].astype("category")
    return X


def main() -> None:
    df = pd.read_parquet(ROOT / "data/claims/claims.parquet")
    hold = df[df["month_index"].between(12, 13)].reset_index(drop=True)
    y = hold["rejected"].to_numpy().astype(int)

    model = joblib.load(ROOT / "supplied_model/model.pkl")
    X = supplied_features(model, hold)
    p = model.predict_proba(X)[:, 1]

    print(f"holdout: {len(hold):,} claims, reject rate {y.mean():.3f}")
    print(f"supplied model   AUC {roc_auc_score(y, p):.4f}   accuracy@0.5 {accuracy_score(y, p >= 0.5):.4f}")
    print(f"approve everything                accuracy     {1 - y.mean():.4f}\n")

    ranking = importance(model, X, y)
    print(f"{'feature':<26}{'AUC drop when shuffled':>24}")
    for name, drop in ranking[:8]:
        print(f"{name:<26}{drop:>24.4f}")
    print("\nFor the top feature, answer before you go on: at the moment the model has "
          "to decide on a claim, does this value exist yet?")


# ════════════════════════════════════════════════════════════════════════════
#  YOURS
# ════════════════════════════════════════════════════════════════════════════

def importance(model, X: pd.DataFrame, y: np.ndarray) -> list[tuple[str, float]]:
    """Return [(feature, mean AUC drop), ...], largest drop first.

    Use sklearn.inspection.permutation_importance with scoring="roc_auc".
    Fix its random_state -- this is a lab about reproducibility -- and use a
    few repeats so one lucky shuffle does not decide the answer.
    """
    from sklearn.inspection import permutation_importance

    r = permutation_importance(model, X, y, scoring="roc_auc", n_repeats=5, random_state=0)
    ranking = [(col, float(mean_drop)) for col, mean_drop in zip(X.columns, r.importances_mean)]
    ranking.sort(key=lambda x: x[1], reverse=True)
    return ranking


if __name__ == "__main__":
    main()
