#!/usr/bin/env python3
"""Run PIT on a pinned Maven checkout and export auditable mutation metrics.

By default this produces a PROJECT-level score. For test-file-level attribution,
provide --test-class and --test-file; PIT is rerun with only that test class.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, shutil, subprocess, sys
import xml.etree.ElementTree as ET
from pathlib import Path

COUNTED = {"KILLED", "SURVIVED", "TIMED_OUT", "MEMORY_ERROR", "RUN_ERROR"}
EXCLUDED = {"NO_COVERAGE", "NON_VIABLE", "NOT_STARTED"}

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",type=Path,required=True)
    ap.add_argument("--repository-id",required=True)
    ap.add_argument("--snapshot-sha",required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--test-class",help="Fully-qualified test class; enables isolated-test attribution")
    ap.add_argument("--test-file",help="Path relative to repository root; required with --test-class")
    ap.add_argument("--target-classes",default="*")
    ap.add_argument("--threads",type=int,default=1)
    ap.add_argument("--timeout",type=int,default=1800)
    ap.add_argument("--pit-version",default="1.17.3")
    args=ap.parse_args()
    repo=args.repo.resolve()
    if not (repo/".git").exists(): ap.error("--repo must be a Git working tree")
    if bool(args.test_class) != bool(args.test_file): ap.error("--test-class and --test-file must be supplied together")
    git=shutil.which("git"); mvn=shutil.which("mvn")
    if not git or not mvn: ap.error("Both git and Maven (mvn) must be on PATH")
    head=subprocess.check_output([git,"-C",str(repo),"rev-parse","HEAD"],text=True).strip()
    if head != args.snapshot_sha: ap.error(f"Checkout SHA mismatch: expected {args.snapshot_sha}, found {head}")
    report=repo/"target"/"pit-reports"/"mutations.xml"
    if report.exists(): report.unlink()
    cmd=[mvn,"-B","-Dstyle.color=never",
         f"-DtargetClasses={args.target_classes}",
         "-DoutputFormats=XML",
         "-DtimestampedReports=false",
         f"-Dthreads={args.threads}",
         f"-DpitestVersion={args.pit_version}"]
    if args.test_class: cmd.append(f"-DtargetTests={args.test_class}")
    cmd += ["org.pitest:pitest-maven:mutationCoverage"]
    log=args.output.with_suffix(".maven.log")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with log.open("w",encoding="utf-8") as out:
        proc=subprocess.run(cmd,cwd=repo,stdout=out,stderr=subprocess.STDOUT,timeout=args.timeout)
    common={"repository_id":args.repository_id,"snapshot_sha":head,
            "test_file":args.test_file or "__PROJECT__",
            "test_class":args.test_class or "",
            "attribution_method":"isolated_test_file" if args.test_class else "project_level_only",
            "measurement_status":"failed","mutation_score":"",
            "killed":0,"survived":0,"timed_out":0,"memory_error":0,
            "run_error":0,"no_coverage":0,"non_viable":0,"not_started":0,
            "total_reported":0,"denominator":0,"pit_version":args.pit_version,
            "maven_exit_code":proc.returncode,"report_path":str(report),
            "report_sha256":"","log_path":str(log)}
    if proc.returncode != 0 or not report.is_file():
        args.output.write_text(json.dumps(common,indent=2),encoding="utf-8")
        print(json.dumps(common,indent=2)); return 1
    tree=ET.parse(report)
    statuses={}
    for node in tree.iter():
        if node.tag.lower().endswith("mutation"):
            s=node.attrib.get("status") or node.findtext("status") or "UNKNOWN"
            statuses[s.upper()]=statuses.get(s.upper(),0)+1
    for s,n in statuses.items():
        key={"KILLED":"killed","SURVIVED":"survived","TIMED_OUT":"timed_out",
             "MEMORY_ERROR":"memory_error","RUN_ERROR":"run_error",
             "NO_COVERAGE":"no_coverage","NON_VIABLE":"non_viable",
             "NOT_STARTED":"not_started"}.get(s)
        if key: common[key]=n
    common["total_reported"]=sum(statuses.values())
    common["denominator"]=sum(common[k] for k in ("killed","survived","timed_out","memory_error","run_error"))
    common["excluded_statuses"]={k:v for k,v in statuses.items() if k not in COUNTED|EXCLUDED}
    common["report_sha256"]=sha256(report)
    if common["denominator"] > 0:
        common["mutation_score"]=common["killed"]/common["denominator"]
        common["measurement_status"]="measured"
    else:
        common["measurement_status"]="not_measured"
    common["status_counts"]=statuses
    args.output.write_text(json.dumps(common,indent=2),encoding="utf-8")
    # Contract-compatible row; project-level rows are intentionally rejected by validate.
    csv_path=args.output.with_suffix(".csv")
    fields=["repository_id","snapshot_sha","test_file","mutation_score","attribution_method","measurement_status"]
    with csv_path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        w.writerow({k:common[k] for k in fields})
    common["contract_csv"]=str(csv_path)
    print(json.dumps(common,indent=2))
    return 0 if common["measurement_status"]=="measured" else 2

if __name__=="__main__": raise SystemExit(main())
