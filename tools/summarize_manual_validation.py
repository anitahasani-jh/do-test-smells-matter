#!/usr/bin/env python3
"""Summarize completed double-coded manual validation; never invent missing labels."""
import argparse, csv, json
from pathlib import Path

def kappa(a, b):
    n = len(a)
    if not n: return None
    po = sum(x == y for x, y in zip(a, b)) / n
    labels = sorted(set(a) | set(b))
    pe = sum((a.count(x)/n) * (b.count(x)/n) for x in labels)
    return None if pe == 1 else (po - pe) / (1 - pe)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv_file")
    p.add_argument("--json-out")
    a = p.parse_args()
    rows = list(csv.DictReader(Path(a.csv_file).open(encoding="utf-8-sig", newline="")))
    allowed = {"confirmed", "not_confirmed", "uncertain"}
    for r in rows:
        for field in ("reviewer1_label", "reviewer2_label", "adjudicated_label"):
            v = (r.get(field) or "").strip()
            if v and v not in allowed:
                raise SystemExit(f"Invalid {field}={v!r}; allowed: {sorted(allowed)}")
    resolved = [r for r in rows if r.get("adjudicated_label") in {"confirmed", "not_confirmed"}]
    tp = sum(r["adjudicated_label"] == "confirmed" for r in resolved)
    fp = sum(r["adjudicated_label"] == "not_confirmed" for r in resolved)
    paired = [r for r in rows if r.get("reviewer1_label") in {"confirmed","not_confirmed"} and r.get("reviewer2_label") in {"confirmed","not_confirmed"}]
    x = [r["reviewer1_label"] for r in paired]
    y = [r["reviewer2_label"] for r in paired]
    cm = {f"{i}|{j}": sum(1 for u,v in zip(x,y) if u==i and v==j)
          for i in ("confirmed","not_confirmed") for j in ("confirmed","not_confirmed")}
    result = {
        "n_rows": len(rows), "adjudicated_resolved_n": len(resolved),
        "true_positive": tp, "false_positive": fp,
        "unresolved_n": len(rows)-len(resolved),
        "precision_resolved": (tp/(tp+fp)) if tp+fp else None,
        "cohen_kappa": kappa(x,y), "kappa_pair_n": len(paired),
        "reviewer_confusion_matrix": cm,
        "warning": "Precision applies to the sampled predicted-positive items; this does not estimate recall or overall accuracy."
    }
    print(json.dumps(result, indent=2))
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(result, indent=2), encoding="utf-8")
if __name__ == "__main__": main()
