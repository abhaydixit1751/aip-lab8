#!/usr/bin/env python3
"""Lab 8 -- rebuild the supplied model N times and measure how much it disagrees
with itself.  PROVIDED -- you do not need to change this file.

    python labs/lab08/rebuild.py              # 3 rebuilds, ~15 s in the course container
    python labs/lab08/rebuild.py --runs 5

Each run executes `supplied_model/train_model.py` exactly as the data-science
team handed it over -- unmodified, in a scratch copy, so nothing in your repo is
touched -- and then scores every one of the 45,365 claims with the model it
produced. The shipped `model.pkl` is included as "shipped", so you also see
whether anyone can rebuild the artefact you were actually given.

What it reports, per pair of builds:
    probs differ    claims whose probability is not bit-identical
    max |dp|        the largest change in probability on any one claim
    decisions       claims whose decision at a threshold of 0.5 flips
"""
from __future__ import annotations

import argparse
import itertools
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def find_root(start: Path) -> Path:
    for d in (start, *start.parents):
        if (d / "pyproject.toml").exists():
            return d
    raise FileNotFoundError(f"no pyproject.toml above {start}")


ROOT = find_root(Path(__file__).resolve().parent)
SUPPLIED = ROOT / "supplied_model"
CLAIMS_PER_DAY = 2_000


def score_all(model, df: pd.DataFrame) -> np.ndarray:
    """Score every claim the way train_model.py's prep() prepares them."""
    X = df[list(model.feature_names_in_)].copy()
    for c in X.columns:
        if X[c].dtype == bool:
            X[c] = X[c].astype(int)
        elif not pd.api.types.is_numeric_dtype(X[c]):
            X[c] = X[c].astype("category")
    return model.predict_proba(X)[:, 1]


def one_build(i: int, workdir: Path) -> tuple[str, object, dict]:
    """Run the untouched training script in a scratch copy of its folder."""
    run_dir = workdir / f"run{i}"
    (run_dir / "supplied_model").mkdir(parents=True)
    shutil.copy(SUPPLIED / "train_model.py", run_dir / "supplied_model" / "train_model.py")
    try:
        (run_dir / "data").symlink_to(ROOT / "data")      # the script reads ../data/claims/...
    except OSError:
        try:
            import _winapi
            _winapi.CreateJunction(str(ROOT / "data"), str(run_dir / "data"))
        except Exception:
            shutil.copytree(ROOT / "data", run_dir / "data")
    r = subprocess.run([sys.executable, "train_model.py"], cwd=run_dir / "supplied_model",
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        sys.exit(f"run {i} failed:\n{r.stderr}")
    reported = {k: float(v) for k, v in re.findall(r"^(accuracy|auc):\s+([\d.]+)", r.stdout, re.M)}
    model = joblib.load(run_dir / "supplied_model" / "model.pkl")
    reported["n_iter"] = int(model.n_iter_)
    return f"run {i}", model, reported


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--threshold", type=float, default=0.5)
    args = ap.parse_args()

    df = pd.read_parquet(ROOT / "data/claims/claims.parquet")
    n = len(df)
    builds: list[tuple[str, np.ndarray]] = []

    shipped = joblib.load(SUPPLIED / "model.pkl")
    builds.append(("shipped", score_all(shipped, df)))
    print(f"{'build':<9}{'accuracy':>10}{'auc':>8}{'n_iter':>8}   (as train_model.py reports them)")
    print(f"{'shipped':<9}{'0.981':>10}{'0.997':>8}{shipped.n_iter_:>8}   (from MODEL_CARD.md)")

    with tempfile.TemporaryDirectory() as tmp:
        for i in range(1, args.runs + 1):
            name, model, rep = one_build(i, Path(tmp))
            builds.append((name, score_all(model, df)))
            print(f"{name:<9}{rep.get('accuracy', float('nan')):>10.4f}"
                  f"{rep.get('auc', float('nan')):>8.4f}{rep['n_iter']:>8}", flush=True)

    t = args.threshold
    print(f"\nAll {n:,} claims, pairwise.  Decision = reject-risk >= {t}\n")
    print(f"{'pair':<22}{'probs differ':>14}{'max |dp|':>10}{'decisions':>11}{'  per day at 2,000/day':>24}")
    worst = 0
    for (a, pa), (b, pb) in itertools.combinations(builds, 2):
        differ = int((pa != pb).sum())
        flips = int(((pa >= t) != (pb >= t)).sum())
        worst = max(worst, flips)
        print(f"{a + ' vs ' + b:<22}{differ:>14,}{np.abs(pa - pb).max():>10.3f}"
              f"{flips:>11,}{flips / n * CLAIMS_PER_DAY:>24.1f}")

    print(f"\nWorst pair: {worst:,} of {n:,} claims ({worst / n:.2%}) get a different decision "
          f"depending on which build of 'the same model' is deployed.")


if __name__ == "__main__":
    main()
