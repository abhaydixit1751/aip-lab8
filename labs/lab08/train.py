#!/usr/bin/env python3
"""Lab 8 -- reproducible training for the claims-triage model.

    python labs/lab08/train.py                                   # params.yaml beside this file
    python labs/lab08/train.py --params labs/lab08/params.yaml --out artifacts/lab08
    python labs/lab08/train.py --no-mlflow                       # what the DVC stage runs
    python labs/lab08/train.py --data /tmp/shuffled.parquet --out /tmp/shuf   # Part B, row order

The job: the same inputs must produce the same model, bit for bit, every time,
on every teammate's laptop. Everything that can change the output belongs in
params.yaml; every output is fingerprinted so "is this the same model?" has a
yes/no answer instead of an opinion.

Outputs (under --out):
    model.joblib          the fitted estimator
    predictions.parquet   claim_id, p_reject for EVERY claim -- the fingerprint set
    metrics.json          holdout metrics, the prediction fingerprint, the environment

Layout: everything above the `YOURS` banner is provided and correct. The three
functions below it raise NotImplementedError. See CODE_GUIDE.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import yaml
from sklearn.metrics import accuracy_score, roc_auc_score

HERE = Path(__file__).resolve().parent


def find_root(start: Path) -> Path:
    """The repository root: the nearest ancestor holding pyproject.toml.

    Not `Path(__file__).parents[2]` -- counting directories breaks the moment
    the script moves one level deeper. Anchor on something that is at the root.
    """
    for d in (start, *start.parents):
        if (d / "pyproject.toml").exists():
            return d
    raise FileNotFoundError(f"no pyproject.toml above {start}")


ROOT = find_root(HERE)


def load_params(path: Path) -> dict:
    p = yaml.safe_load(path.read_text(encoding="utf-8"))
    p["features"].setdefault("boolean", [])
    return p


def fingerprint(probs: np.ndarray) -> str:
    """sha256 of the raw float64 bytes. Equal iff every probability is bit-identical."""
    return hashlib.sha256(np.ascontiguousarray(probs, dtype=np.float64).tobytes()).hexdigest()


def environment() -> dict:
    """Recorded with every run, so a mismatch can be explained, not just detected."""
    return {
        "python": platform.python_version(),
        "machine": platform.machine(),
        "system": platform.system(),
        "sklearn": sklearn.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS", "default"),
        "in_container": os.environ.get("AIP2_IN_CONTAINER") == "1",
    }


def log_to_mlflow(p: dict, metrics: dict, out: Path) -> None:
    """One MLflow run per training. The UI: see RUNSHEET.md, step 3.5."""
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    import mlflow

    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("lab08-claims-triage")
    feats = p["features"]
    with mlflow.start_run(run_name=p.get("run_name", "train")):
        mlflow.log_params({
            "random_state": p["model"].get("random_state"),
            **p["model"]["hyperparameters"],
            "n_features": sum(len(feats[k]) for k in ("numeric", "categorical", "boolean")),
            "leak_dropped": "assessor_note_length" not in feats["numeric"],
        })
        mlflow.log_metrics({k: v for k, v in metrics.items() if isinstance(v, (int, float))})
        mlflow.set_tag("prediction_fingerprint", metrics["prediction_fingerprint"])
        mlflow.log_artifact(str(out / "metrics.json"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default=str(HERE / "params.yaml"))
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "lab08"))
    ap.add_argument("--no-mlflow", action="store_true")
    ap.add_argument("--data", help="use this parquet instead of data.path (the shuffled-row test)")
    args = ap.parse_args()

    p = load_params(Path(args.params))
    if args.data:
        p["data"]["path"] = str(Path(args.data).resolve())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    label = p["data"]["label"]

    df, train, hold = load_data(p)
    model = build_model(p)
    model.fit(prep(train, p), train[label])

    p_hold = model.predict_proba(prep(hold, p))[:, 1]
    p_all = model.predict_proba(prep(df, p))[:, 1]
    y_hold = hold[label].to_numpy()

    metrics = {
        "holdout_auc": round(float(roc_auc_score(y_hold, p_hold)), 6),
        "holdout_accuracy_at_0.5": round(float(accuracy_score(y_hold, p_hold >= 0.5)), 6),
        "holdout_reject_rate": round(float(y_hold.mean()), 6),
        "n_iter": int(model.n_iter_),
        "prediction_fingerprint": fingerprint(p_all),
        "environment": environment(),
    }

    joblib.dump(model, out / "model.joblib")
    pd.DataFrame({"claim_id": df["claim_id"].to_numpy(), "p_reject": p_all}).to_parquet(
        out / "predictions.parquet", index=False)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    if not args.no_mlflow:
        log_to_mlflow(p, metrics, out)

    print(json.dumps({k: v for k, v in metrics.items() if k != "environment"}, indent=2))


# ════════════════════════════════════════════════════════════════════════════
#  YOURS -- three functions. Each one hides a way for two runs to disagree.
# ════════════════════════════════════════════════════════════════════════════

def load_data(p: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (all claims, training rows, holdout rows).

    Read the path, label and month ranges from params -- no literals here.
    `df` is also what gets fingerprinted, so its row order must not depend on
    how the file happened to be written. Ask: if someone re-exported the parquet
    with the rows shuffled, would your fingerprint change?
    """
    raise NotImplementedError("Part B -- see CODE_GUIDE.md")


def prep(rows: pd.DataFrame, p: dict) -> pd.DataFrame:
    """Turn claim rows (train, holdout, or all) into the model's feature frame.

    Columns come from params -- numeric, then categorical, then boolean.
    Categoricals become pandas `category` dtype (the model reads them with
    `categorical_features="from_dtype"`); booleans become int.

    The supplied script let pandas infer the categories from whatever rows it
    was handed. A classic source of silent disagreement -- or is it, here?
    Test it before you "fix" it: CONCEPTS.md, "Category order".
    """
    raise NotImplementedError("Part B -- see CODE_GUIDE.md")


def build_model(p: dict):
    """Return an unfitted HistGradientBoostingClassifier configured from params.

    Use your Part A evidence: rebuild.py showed `n_iter` changing between runs
    of identical input. Find out why (scikit-learn docs for this estimator:
    `early_stopping`, `validation_fraction`, `random_state`), and make the fix
    a value in params.yaml, not a literal in code.
    """
    raise NotImplementedError("Part B -- see CODE_GUIDE.md")


if __name__ == "__main__":
    main()
