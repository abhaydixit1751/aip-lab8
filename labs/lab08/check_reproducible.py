#!/usr/bin/env python3
"""Lab 8 -- are two training outputs the same model?  PROVIDED -- do not weaken it.

    python labs/lab08/check_reproducible.py artifacts/lab08 /tmp/clone/artifacts/lab08
    python labs/lab08/check_reproducible.py A B --threshold 0.018

Each argument is a folder written by your train.py, holding `metrics.json` and
`predictions.parquet`. The answer is one of three levels, strongest first:

    BIT-IDENTICAL        every probability for every claim is the same float64
    DECISION-IDENTICAL   probabilities differ, but no claim changes decision at
                         any threshold you pass
    DIFFERENT            at least one claim gets a different decision

Exit code 0 = bit-identical, 1 = not bit-identical, 2 = CANNOT COMPARE.

Why this script refuses so readily
----------------------------------
The first version of this check, written while building the reference solution,
compared two fingerprints that were both EMPTY -- training had crashed -- and
printed "bit-identical". Two empty strings are equal. So this version refuses
to compare anything it cannot verify: a missing file, a missing key, a
fingerprint that is not 64 hex characters, or a fingerprint that does not match
the predictions sitting next to it (a stale metrics.json from an earlier run).
A check that can pass on nothing is worse than no check.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HEX64 = re.compile(r"^[0-9a-f]{64}$")


class CannotCompare(Exception):
    pass


def fingerprint(probs: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(probs, dtype=np.float64).tobytes()).hexdigest()


def load(folder: Path) -> tuple[dict, pd.DataFrame]:
    mpath, ppath = folder / "metrics.json", folder / "predictions.parquet"
    for f in (mpath, ppath):
        if not f.is_file():
            raise CannotCompare(f"{f} does not exist -- did training finish?")
    try:
        metrics = json.loads(mpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CannotCompare(f"{mpath} is not valid JSON: {exc}") from exc
    fp = metrics.get("prediction_fingerprint")
    if not isinstance(fp, str) or not HEX64.match(fp):
        raise CannotCompare(f"{mpath}: prediction_fingerprint is {fp!r}, not a 64-character sha256")

    preds = pd.read_parquet(ppath)
    if list(preds.columns[:2]) != ["claim_id", "p_reject"]:
        raise CannotCompare(f"{ppath}: expected columns claim_id, p_reject; found {list(preds.columns)}")
    if len(preds) == 0:
        raise CannotCompare(f"{ppath} has no rows")
    if preds["p_reject"].isna().any():
        raise CannotCompare(f"{ppath}: {int(preds['p_reject'].isna().sum())} missing probabilities")
    actual = fingerprint(preds["p_reject"].to_numpy())
    if actual != fp:
        raise CannotCompare(f"{folder}: metrics.json says {fp[:12]}... but predictions.parquet "
                            f"hashes to {actual[:12]}... -- one of them is stale. Retrain.")
    return metrics, preds


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--threshold", type=float, action="append",
                    help="decision threshold(s) to check; repeatable. Default 0.5")
    args = ap.parse_args()
    thresholds = args.threshold or [0.5]

    try:
        ma, pa = load(args.a)
        mb, pb = load(args.b)
        if not pa["claim_id"].equals(pb["claim_id"]):
            raise CannotCompare("the two runs scored different claims, or in a different order. "
                                "Sort by claim_id before predicting.")
    except CannotCompare as exc:
        print(f"CANNOT COMPARE: {exc}")
        sys.exit(2)

    ea, eb = ma.get("environment", {}), mb.get("environment", {})
    keys = sorted(set(ea) | set(eb))
    if keys:
        print(f"{'environment':<16}{'A':<22}{'B':<22}")
        for k in keys:
            va, vb = str(ea.get(k, "-")), str(eb.get(k, "-"))
            print(f"{k:<16}{va:<22}{vb:<22}{'' if va == vb else '<- differs'}")
        print()

    fa, fb = ma["prediction_fingerprint"], mb["prediction_fingerprint"]
    print(f"A  {fa}\nB  {fb}\n")
    if fa == fb:
        print(f"BIT-IDENTICAL -- all {len(pa):,} probabilities match exactly.")
        sys.exit(0)

    xa, xb = pa["p_reject"].to_numpy(), pb["p_reject"].to_numpy()
    differ = int((xa != xb).sum())
    print(f"{differ:,} of {len(xa):,} probabilities differ; largest |dp| = {np.abs(xa - xb).max():.3g}")
    flips_any = 0
    for t in thresholds:
        flips = int(((xa >= t) != (xb >= t)).sum())
        flips_any += flips
        print(f"  threshold {t:<6}  {flips:,} decisions differ")
    print("\nDECISION-IDENTICAL at the threshold(s) checked." if flips_any == 0 else
          "\nDIFFERENT -- some claims get a different decision.")
    sys.exit(1)


if __name__ == "__main__":
    main()
