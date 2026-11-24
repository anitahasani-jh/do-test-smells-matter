# E-value and unmeasured-confounding sensitivity protocol

**Status: utility and protocol added for team review. Not team-approved, not preregistered, and not run on empirical study estimates.**

## What this analysis answers

The E-value quantifies how strongly an unmeasured confounder would need to be associated with both treatment and outcome (on the risk-ratio scale), conditional on measured covariates, to explain away an observed risk ratio. It is a sensitivity analysis, not proof that unmeasured confounding is absent.

## Critical estimand restriction

`tools/evalue_sensitivity.py` accepts an adjusted **risk ratio (RR)** and optionally its confidence interval. It does **not** accept a continuous-outcome DML coefficient, mutation score, odds ratio, hazard ratio, or arbitrary regression coefficient. The current DML utility estimates a partially-linear effect for a continuous outcome such as `post_change_count`; its coefficient cannot be inserted into this E-value calculator. If the team wants an E-values analysis, define a defensible binary outcome and estimate an adjusted RR with a method appropriate to the data and estimand. Do not dichotomize outcomes solely to obtain an E-value without a prespecified scientific justification.

For a protective RR below 1, the implementation inverts the RR before applying the standard formula. The confidence-interval E-value uses the limit closest to the null (RR=1); if the interval crosses 1, the CI E-value is 1.

## Run (template)

```powershell
python tools/evalue_sensitivity.py --rr 1.80 --ci-lower 1.20 --ci-upper 2.40 --output results/evalue/example.json
```

Optional explicit unmeasured-confounder scenario:

```powershell
python tools/evalue_sensitivity.py --rr 1.80 --rr-ua 2.0 --rr-ay 2.0
```

The numerical values above are **illustrative command arguments only**, not study findings. Replace them only with a justified estimate and interval from the actual analysis.

## Interpretation and limitations

- The point E-value describes the minimum equal-strength associations (RR scale) required under the E-value framework; unequal-strength scenarios can be assessed using the bias-factor function in the script.
- The confidence-interval E-value is the robustness of the confidence limit closest to the null, not a second point estimate.
- E-values depend on a valid effect measure, correct direction, and appropriate interval. They do not address selection bias, measurement error, model misspecification, positivity violations, or clustering automatically.
- For files nested within repositories, the RR confidence interval must account for repository clustering before reporting a confidence-limit E-value. An IID interval is provisional and should not be treated as confirmatory.
- Report the assumed binary outcome definition, time window, treatment definition, adjustment set, RR estimator, cluster-robust uncertainty method, and rationale for plausible confounder strengths.
- Compare PSM, DML, and regression estimates only when they target compatible estimands and populations. E-value is supplementary and does not validate a DAG or identify confounders.

## Completion checklist

- [x] RR-scale E-value point estimate calculator.
- [x] Confidence-interval E-value and null-crossing logic.
- [x] Optional bias-factor scenario for specified confounder associations.
- [x] Unit tests with analytic checks.
- [ ] Team approves a scientifically meaningful binary outcome and RR estimand.
- [ ] Estimate RR and repository-cluster-aware confidence interval from empirical data.
- [ ] Choose and justify plausible unmeasured-confounder strength scenarios.
- [ ] Run on real data and report without causal overclaiming.
