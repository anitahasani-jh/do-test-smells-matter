#!/usr/bin/env python3
"""Create a reproducible, stratified manual-review sample from actual smells.csv."""
from __future__ import annotations
import argparse, csv, random, sys
from collections import defaultdict
from pathlib import Path

FIELDS = [
    "sample_id", "repository_id", "snapshot_sha", "test_file", "smell_type",
    "detector_prediction", "smell_status", "reviewer1_label", "reviewer1_evidence",
    "reviewer2_label", "reviewer2_evidence", "adjudicated_label", "adjudication_note"
]

def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "1.0"}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smells", required=True, help="Actual pipeline smells.csv")
    ap.add_argument("--output", required=True)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    if args.n < 1:
        ap.error("--n must be positive")
    with Path(args.smells).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {"repository_id", "snapshot_sha", "test_file", "smell_type", "smell_present", "smell_status"}
    if not rows or not required.issubset(rows[0]):
        raise SystemExit(f"Input must contain columns: {', '.join(sorted(required))}")
    eligible = []
    seen = set()
    for r in rows:
        status = str(r.get("smell_status", "")).strip().lower()
        key = (r["repository_id"], r["snapshot_sha"], r["test_file"], r["smell_type"])
        if status not in {"measured", "valid", "ok"} or not truthy(r.get("smell_present", "")) or key in seen:
            continue
        seen.add(key)
        eligible.append(r)
    if len(eligible) < args.n:
        raise SystemExit(
            f"Only {len(eligible)} unique measured positive predictions are available; "
            f"{args.n} are required. Do not duplicate records. Collect more eligible data first."
        )
    groups = defaultdict(list)
    for r in eligible:
        groups[r["smell_type"]].append(r)
    rng = random.Random(args.seed)
    for group in groups.values():
        rng.shuffle(group)
    selected = []
    names = sorted(groups)
    # Round-robin across smell categories, avoiding domination by common smells.
    while len(selected) < args.n:
        progressed = False
        for name in names:
            if groups[name] and len(selected) < args.n:
                selected.append(groups[name].pop())
                progressed = True
        if not progressed:
            break
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, r in enumerate(selected, 1):
            w.writerow({
                "sample_id": f"MV{i:03d}", "repository_id": r["repository_id"],
                "snapshot_sha": r["snapshot_sha"], "test_file": r["test_file"],
                "smell_type": r["smell_type"], "detector_prediction": "positive",
                "smell_status": r["smell_status"], "reviewer1_label": "",
                "reviewer1_evidence": "", "reviewer2_label": "",
                "reviewer2_evidence": "", "adjudicated_label": "", "adjudication_note": ""
            })
    print(f"Created {len(selected)} unique positive-prediction review rows: {out}")
    print(f"Seed={args.seed}; eligible_population={len(eligible)}; smell_types={len(groups)}")
    print("This is an annotation template; manual labels are still required.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
