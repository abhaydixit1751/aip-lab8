"""Score the running service against eval/cases.jsonl. Standard library only.

    python evaluate.py --url http://api:8000             print the metrics
    python evaluate.py --url http://api:8000 --min 1.0   ...and exit 1 below the gate
"""

import argparse
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://api:8000")
p.add_argument("--min", type=float, default=None, help="gate: minimum accuracy")
args = p.parse_args()

cases = [json.loads(line) for line in (Path(__file__).parent / "cases.jsonl").read_text().splitlines() if line]
correct, latencies = 0, []
for case in cases:
    t0 = time.perf_counter()
    with urllib.request.urlopen(f"{args.url}/hello/{case['name']}", timeout=5) as r:
        answer = json.load(r)["message"]
    latencies.append((time.perf_counter() - t0) * 1000)
    correct += answer == case["expect"]

accuracy = correct / len(cases)
print(f"cases={len(cases)} accuracy={accuracy:.2f} p50_ms={statistics.median(latencies):.1f}")
if args.min is not None:
    verdict = "PASS" if accuracy >= args.min else "FAIL"
    print(f"gate: accuracy {accuracy:.2f} >= {args.min:.2f}? {verdict}")
    sys.exit(0 if verdict == "PASS" else 1)
