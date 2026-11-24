#!/usr/bin/env python3
"""One-to-one propensity-score matching for a single binary test-smell treatment.

This is an analysis utility, not proof of causal identification. It deliberately
requires explicit covariates and preserves an audit trail for excluded rows.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _smd(a: pd.Series, b: pd.Series) -> float:
    x = pd.to_numeric(a, errors="coerce").dropna().astype(float)
    y = pd.to_numeric(b, errors="coerce").dropna().astype(float)
    if len(x) == 0 or len(y) == 0:
        return float("nan")
    pooled = math.sqrt((x.var(ddof=1) + y.var(ddof=1)) / 2) if len(x) > 1 and len(y) > 1 else 0.0
    if pooled == 0:
        return 0.0 if x.mean() == y.mean() else float("inf")
    return float((x.mean() - y.mean()) / pooled)


def _design_matrix(frame: pd.DataFrame, covariates: Sequence[str]):
    numeric = [c for c in covariates if pd.api.types.is_numeric_dtype(frame[c])]
    categorical = [c for c in covariates if c not in numeric]
    transformers = []
    if numeric:
        num_pipe = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
        transformers.append(("num", num_pipe, numeric))
    if categorical:
        cat_pipe = Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ])
        transformers.append(("cat", cat_pipe, categorical))
    return ColumnTransformer(transformers=transformers, remainder="drop")


def run_psm(
    input_csv: Path,
    output_dir: Path,
    treatment_col: str,
    outcome_col: str,
    covariates: Sequence[str],
    id_cols: Sequence[str],
    exact_match_cols: Sequence[str],
    caliper: float = 0.2,
) -> dict:
    df = pd.read_csv(input_csv, dtype={c: "string" for c in id_cols if c})
    required = [treatment_col, outcome_col, *covariates, *id_cols, *exact_match_cols]
    missing_cols = sorted(set(required) - set(df.columns))
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    if not covariates:
        raise ValueError("At least one pre-treatment covariate is required")
    if treatment_col in covariates or outcome_col in covariates:
        raise ValueError("Treatment and outcome cannot be propensity covariates")

    work = df.copy()
    work["_treatment"] = pd.to_numeric(work[treatment_col], errors="coerce")
    work["_outcome"] = pd.to_numeric(work[outcome_col], errors="coerce")
    audit = {
        "input_rows": int(len(work)),
        "treatment_missing_or_nonbinary": int((~work["_treatment"].isin([0, 1])).sum()),
        "outcome_missing_or_nonnumeric": int(work["_outcome"].isna().sum()),
        "covariate_rows_with_any_missing": int(work[list(covariates)].isna().any(axis=1).sum()),
        "caliper_logit_ps_sd": float(caliper),
        "matching": "1:1 nearest-neighbour, greedy, without replacement",
        "exact_match_columns": list(exact_match_cols),
        "covariates": list(covariates),
        "treatment": treatment_col,
        "outcome": outcome_col,
    }
    # Do not silently impute missing covariates: missingness is handled explicitly
    # because imputation choices need to be preregistered for this study.
    valid = work["_treatment"].isin([0, 1]) & work["_outcome"].notna() & ~work[list(covariates)].isna().any(axis=1)
    for col in exact_match_cols:
        valid &= work[col].notna()
    work = work.loc[valid].copy().reset_index(drop=False).rename(columns={"index": "_source_row"})
    if work.empty or work["_treatment"].nunique() != 2:
        raise ValueError("After exclusions, both treatment groups must be present")
    if work["_treatment"].value_counts().min() < 2:
        raise ValueError("At least two observations in each treatment group are required")

    # Categorical vs numeric columns are inferred from CSV dtypes. Convert
    # numeric-looking string covariates only when the caller's CSV stores them numeric.
    preprocessor = _design_matrix(work, covariates)
    model = Pipeline([
        ("preprocess", preprocessor),
        ("logistic", LogisticRegression(max_iter=3000, solver="lbfgs")),
    ])
    model.fit(work[list(covariates)], work["_treatment"].astype(int))
    work["propensity_score"] = model.predict_proba(work[list(covariates)])[:, 1]
    work["logit_ps"] = _logit(work["propensity_score"].to_numpy())
    sd_logit = float(work["logit_ps"].std(ddof=1))
    if not np.isfinite(sd_logit) or sd_logit <= 0:
        raise ValueError("Estimated propensity scores have no usable variation")
    caliper_width = caliper * sd_logit

    treated = work[work["_treatment"] == 1].copy()
    controls = work[work["_treatment"] == 0].copy()
    lower = max(float(treated.propensity_score.min()), float(controls.propensity_score.min()))
    upper = min(float(treated.propensity_score.max()), float(controls.propensity_score.max()))
    treated = treated[treated.propensity_score.between(lower, upper)]
    controls = controls[controls.propensity_score.between(lower, upper)]
    controls_by_stratum: dict[tuple, list[int]] = {}
    for idx, row in controls.iterrows():
        key = tuple(str(row[c]) for c in exact_match_cols)
        controls_by_stratum.setdefault(key, []).append(idx)

    used_controls: set[int] = set()
    pairs = []
    # Deterministic order: treated units sorted by propensity score then original row.
    for tidx, trow in treated.sort_values(["logit_ps", "_source_row"]).iterrows():
        key = tuple(str(trow[c]) for c in exact_match_cols)
        candidates = [cidx for cidx in controls_by_stratum.get(key, []) if cidx not in used_controls]
        if not candidates:
            continue
        distances = [(abs(float(trow.logit_ps - work.loc[cidx, "logit_ps"])), cidx) for cidx in candidates]
        distance, cidx = min(distances, key=lambda z: (z[0], int(work.loc[z[1], "_source_row"])))
        if distance > caliper_width:
            continue
        used_controls.add(cidx)
        crow = work.loc[cidx]
        pair = {"pair_id": len(pairs) + 1, "treated_source_row": int(trow._source_row),
                "control_source_row": int(crow._source_row), "logit_ps_distance": float(distance),
                "treated_ps": float(trow.propensity_score), "control_ps": float(crow.propensity_score),
                "treated_outcome": float(trow._outcome), "control_outcome": float(crow._outcome),
                "outcome_difference_treated_minus_control": float(trow._outcome - crow._outcome)}
        for col in id_cols:
            pair[f"treated_{col}"] = str(trow[col])
            pair[f"control_{col}"] = str(crow[col])
        for col in exact_match_cols:
            pair[f"stratum_{col}"] = str(trow[col])
        pairs.append(pair)

    output_dir.mkdir(parents=True, exist_ok=True)
    pairs_df = pd.DataFrame(pairs)
    pairs_path = output_dir / "psm_matched_pairs.csv"
    pairs_df.to_csv(pairs_path, index=False)
    matched_t = work[work["_source_row"].isin([p["treated_source_row"] for p in pairs])]
    matched_c = work[work["_source_row"].isin([p["control_source_row"] for p in pairs])]
    balance_rows = []
    for col in covariates:
        if pd.api.types.is_numeric_dtype(work[col]):
            before = _smd(work.loc[work._treatment == 1, col], work.loc[work._treatment == 0, col])
            after = _smd(matched_t[col], matched_c[col]) if len(pairs) else float("nan")
            balance_rows.append({"covariate": col, "smd_before": before, "smd_after": after,
                                 "abs_smd_after": abs(after) if np.isfinite(after) else np.nan})
        else:
            levels = sorted(set(work[col].astype(str)))
            for level in levels:
                treated_before = (work.loc[work._treatment == 1, col].astype(str) == level).astype(float)
                control_before = (work.loc[work._treatment == 0, col].astype(str) == level).astype(float)
                treated_after = (matched_t[col].astype(str) == level).astype(float)
                control_after = (matched_c[col].astype(str) == level).astype(float)
                before = _smd(treated_before, control_before)
                after = _smd(treated_after, control_after) if len(pairs) else float("nan")
                balance_rows.append({"covariate": f"{col}={level}", "smd_before": before, "smd_after": after,
                                     "abs_smd_after": abs(after) if np.isfinite(after) else np.nan})
    balance_df = pd.DataFrame(balance_rows)
    balance_path = output_dir / "psm_balance.csv"
    balance_df.to_csv(balance_path, index=False)

    differences = pairs_df["outcome_difference_treated_minus_control"] if len(pairs_df) else pd.Series(dtype=float)
    outcome_type = "binary" if set(work["_outcome"].unique()).issubset({0.0, 1.0}) else "continuous_or_count"
    summary = {
        "status": "matched" if len(pairs) else "no_pairs_matched",
        "audit": audit,
        "analysis_rows_after_exclusions": int(len(work)),
        "treated_before_matching": int((work._treatment == 1).sum()),
        "control_before_matching": int((work._treatment == 0).sum()),
        "treated_inside_common_support": int(len(treated)),
        "control_inside_common_support": int(len(controls)),
        "matched_pairs": int(len(pairs)),
        "treated_unmatched_after_support": int(len(treated) - len(pairs)),
        "caliper_width_logit_ps": float(caliper_width),
        "common_support_propensity_range": [lower, upper],
        "outcome_type": outcome_type,
        "matched_att_descriptive": float(differences.mean()) if len(differences) else None,
        "matched_difference_sd": float(differences.std(ddof=1)) if len(differences) > 1 else None,
        "balance_rule_of_thumb": "absolute standardized mean difference < 0.10; diagnostic only",
        "max_abs_smd_after": float(balance_df.abs_smd_after.max()) if not balance_df.empty and balance_df.abs_smd_after.notna().any() else None,
        "interpretation_warning": (
            "Matched contrast is descriptive until DAG, covariate set, overlap, balance, missingness, "
            "cluster dependence, and identification assumptions are reviewed. Standard errors/CI are not "
            "reported because repository clustering and design approval are pending."
        ),
        "files": {"matched_pairs": pairs_path.name, "balance": balance_path.name},
    }
    (output_dir / "psm_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="CSV with one row per eligible test file")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--treatment", required=True, help="One binary smell column coded 0/1")
    parser.add_argument("--outcome", required=True, help="One numeric post-baseline outcome")
    parser.add_argument("--covariates", required=True, help="Comma-separated baseline/pre-treatment covariate columns")
    parser.add_argument("--id-cols", default="repository_id,snapshot_sha,test_file", help="Comma-separated identifier columns")
    parser.add_argument("--exact-match-cols", default="", help="Optional exact strata, e.g. repository_id")
    parser.add_argument("--caliper", type=float, default=0.2, help="Caliper as fraction of SD of logit propensity score")
    args = parser.parse_args()
    if args.caliper <= 0:
        parser.error("--caliper must be positive")
    summary = run_psm(args.input, args.output_dir, args.treatment, args.outcome,
                      [x.strip() for x in args.covariates.split(",") if x.strip()],
                      [x.strip() for x in args.id_cols.split(",") if x.strip()],
                      [x.strip() for x in args.exact_match_cols.split(",") if x.strip()], args.caliper)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
