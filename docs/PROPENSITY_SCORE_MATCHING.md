# Propensity Score Matching (PSM) protocol and implementation

**Status: implementation + analysis protocol for team review. NOT preregistered, NOT approved as the final causal design, and NOT run on empirical study data.**

## 1. Purpose and estimand

PSM is planned as a sensitivity/adjustment analysis for **one smell type at a time**. The treatment is the baseline `smell_present` flag (0/1) for that smell. The proposed target is the ATT among treated test files that have comparable untreated files in the common-support region. This target is narrower than all test files: treated files without overlap or a valid match are excluded.

The unit remains one Java test file at one immutable baseline snapshot, keyed by `(repository_id, snapshot_sha, test_file)`. Outcomes must be measured strictly after baseline. A file-change count is maintenance activity, not automatically a defect. A commit-message regex is only a potential-bugfix proxy. A project-level PIT score must never be duplicated across file rows.

## 2. Implemented method

`tools/propensity_score_matching.py` implements:

1. A separate binary treatment model for one smell label using logistic regression.
2. Numeric covariate median imputation + standardization and categorical most-frequent imputation + one-hot encoding **inside the propensity model**. However, the analysis dataset is complete-case on the specified covariates; rows with any missing covariate are excluded before fitting, so imputation is currently a defensive pipeline step rather than a missing-data remedy.
3. Common-support restriction based on the intersection of observed propensity-score ranges in the treated and control groups.
4. Greedy 1:1 nearest-neighbour matching without replacement on the logit propensity score.
5. Default caliper = 0.2 × SD(logit propensity score); this is a starting convention and must be reviewed/preregistered.
6. Optional exact matching strata, e.g. `repository_id`, to avoid pairing files across projects. Exact matching can sharply reduce the matched sample; use only when the estimand and sample support justify it.
7. Outputs: matched pairs, standardized mean-difference balance table before/after matching, and a JSON audit/summary.

The matching order is deterministic (treated units sorted by logit score and original input row). It is greedy, not globally optimal. Results can differ from optimal matching or matching with replacement; this limitation must be stated.

## 3. Input contract

Prepare a CSV with one row per eligible test file and at least:

- `repository_id`, `snapshot_sha`, `test_file`
- one binary smell column coded exactly 0/1 (not a missing detector result)
- one numeric post-baseline outcome
- explicitly chosen baseline/pre-baseline covariates from the approved smell-specific DAG

Do not put outcomes, post-baseline activity, mediators, build-success indicators, or collider/selection variables into the propensity covariates. Do not use a single propensity model for several smell types. Do not include a covariate merely because it predicts treatment; it must be defensible as a pre-treatment common cause under the DAG. Inspect whether a candidate such as `test_loc` or `assert_count` overlaps mechanically with the smell detector definition.

Categorical columns should be stored as strings/categories; numeric columns as numeric values. Rows with missing treatment, outcome, covariates, or exact-match keys are excluded and counted in the audit. Missing treatment must not be recoded as 0.

## 4. Example command (template only)

```powershell
python tools/propensity_score_matching.py `
  --input data/analysis_input.csv `
  --output-dir results/psm/eager_test_smell/ `
  --treatment eager_test_smell `
  --outcome post_change_count `
  --covariates test_loc,assert_count,test_age_days,prior_file_changes,project_age_days,project_activity,test_framework `
  --id-cols repository_id,snapshot_sha,test_file `
  --exact-match-cols repository_id `
  --caliper 0.2
```

Replace every placeholder with a real column present in the final analysis CSV. The example is not a claim that these variables have all been collected or approved. If `repository_id` exact matching is used, each repository needs both treated and control files and sufficient within-repository overlap.

Install analysis dependencies from the project root:

```powershell
python -m pip install -e ".[analysis,dev]"
```

## 5. Required diagnostics and interpretation

Review `results/psm/.../psm_summary.json`, `psm_balance.csv`, and `psm_matched_pairs.csv` together.

- Report initial treated/control counts, missingness exclusions, common support, matched pairs, unmatched treated units, and exact-match strata.
- Assess balance using absolute standardized mean differences; `< 0.10` is a common diagnostic rule of thumb, not proof of no confounding. Inspect every covariate, not only the maximum.
- Plot propensity-score distributions before/after matching as a recommended next diagnostic; this script does not yet generate plots.
- Verify no pair violates exact-match strata and manually inspect extreme scores / influential repositories.
- Report the matched treated population and avoid generalizing to unmatched treated files.
- Files are nested within repositories. The script intentionally does **not** report naive p-values, confidence intervals, or standard errors. The matched contrast is descriptive until a repository-aware uncertainty procedure (e.g. cluster bootstrap at repository level, with a carefully defined resampling/matching protocol) is implemented and validated.
- PSM cannot remove unmeasured confounding (`U`), fix selection bias, or prove causal identification. If overlap/balance is poor, do not force a causal estimate; report the limitation and consider alternative estimators / target population.

## 6. PIT-specific warning

Do not feed project-level mutation scores into file-level PSM rows. PIT can be an outcome for this file-level analysis only after per-test-file attribution is demonstrated and validated. Otherwise, define a separate project/module-level dataset, DAG, treatment, and estimand, and perform matching at that same level.

## 7. Current completion state

- [x] Reproducible PSM utility added.
- [x] Matched-pair, balance, and audit outputs defined.
- [x] Synthetic unit test added (software test only; not research data).
- [ ] Team approves smell-specific DAG, covariate set, estimand, caliper, matching strata, and missing-data policy.
- [ ] Final analysis dataset with real observations is assembled and validated.
- [ ] PSM is run on the real dataset and overlap/balance diagnostics reviewed.
- [ ] Repository-aware uncertainty and sensitivity analyses are implemented and reviewed.

**No empirical PSM results are included in this package.**
