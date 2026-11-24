# Double Machine Learning (DML) protocol

**Status: implementation and proposed analysis protocol for team review. Not preregistered, not team-approved, and not run on empirical study data.**

## Purpose and estimand

The utility implements cross-fitted partially-linear DML for a binary, smell-specific treatment and a continuous post-baseline outcome. The coefficient is interpreted as a partially-linear treatment effect only under the assumptions listed in the JSON audit. Run one smell type and one outcome per analysis. The observational unit remains a Java test file at a pinned baseline snapshot.

## Implementation

`tools/double_machine_learning.py`:
- Fits nuisance functions for the outcome regression E[Y|X] and treatment propensity E[A|X].
- Uses stratified K-fold cross-fitting so each row's nuisance predictions are out-of-fold.
- Supports random-forest or histogram-gradient-boosting nuisance learners.
- Clips estimated propensity scores to [0.01, 0.99] for numerical stability and reports clipping diagnostics.
- Estimates the partially-linear coefficient with an orthogonal residual-on-residual score.
- Writes out-of-fold predictions/residuals and an audit JSON containing sample counts, estimate, and provisional IID interval.

## Example (template only)

```powershell
python tools/double_machine_learning.py `
  --input data/analysis_input.csv `
  --output-dir results/dml/eager_test_smell/ `
  --treatment eager_test_smell `
  --outcome post_change_count `
  --covariates test_age_days,prior_file_changes,project_age_days,project_activity,test_framework `
  --id-cols repository_id,snapshot_sha,test_file `
  --folds 5 --seed 7 --learner random_forest
```

Only include DAG-approved, pre-treatment covariates. Do not include post-baseline variables, mediators, outcomes, build-success selection indicators, or colliders. Avoid mechanically overlapping covariates such as assertion count if the selected smell definition itself is based on assertion structure; justify such choices in advance. A separate model is required for each smell/outcome pair.

## Interpretation and limitations

- DML does not make observational data causal by itself. Conditional exchangeability/no unmeasured confounding, overlap, consistency, and an appropriate partially-linear specification remain substantive assumptions.
- The reported interval is IID and **not** repository-cluster-robust. Since test files are nested within repositories, it is provisional only. Before confirmatory inference, implement and validate a repository-level cluster bootstrap that repeats the full nuisance fitting and estimation process.
- The current script does not automatically select covariates from the DAG, test balance, estimate heterogeneous effects, handle count-outcome-specific estimands, or correct selection bias.
- Propensity clipping is a numerical safeguard, not proof of overlap. Inspect propensity distributions and clipping fraction; report weak overlap and avoid overclaiming.
- A project-level PIT score must never be copied onto test-file rows. PIT is eligible as a file-level outcome only after credible per-test attribution has been validated; otherwise analyze at project/module level with a matching unit and DAG.
- Compare DML with PSM and simpler regression as sensitivity analyses; disagreement is a finding to investigate, not a reason to choose the preferred estimate.

## Completion checklist

- [x] Cross-fitted DML utility and audit outputs added.
- [x] Synthetic software test added.
- [ ] Team approves estimand, smell-specific DAG, covariates, outcome, learner, and fold count.
- [ ] Real analysis dataset is assembled and validated.
- [ ] Run on empirical data and inspect overlap, missingness, and nuisance diagnostics.
- [ ] Implement repository-cluster bootstrap before confirmatory uncertainty claims.
- [ ] Compare against PSM and regression sensitivity analyses.

**No empirical DML estimate is included in this package.**
