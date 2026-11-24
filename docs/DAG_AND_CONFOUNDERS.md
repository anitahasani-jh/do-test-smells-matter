# Proposed causal DAG and confounder protocol

**Status: team-review proposal — NOT approved, preregistered, or empirically validated.**  
**Owner:** Analyst, with Developer and Experimenter review.  
**Version:** 1.0 (2026-11-20)

This document turns the current research contract into a reviewable starting point. It does not claim that the proposed adjustment set identifies a causal effect. All definitions, time windows, exclusions, and estimands must be agreed by all three team members and the instructor before outcome analysis.

## 1. Target question and unit

For each smell type, the proposed question is: *among eligible Java test files observed at a pinned baseline snapshot, what is the association / (if identification assumptions hold) causal effect of the presence of that smell at baseline on a prespecified post-baseline outcome?*

- **Unit:** one Java test file at `snapshot_sha`, keyed by `(repository_id, snapshot_sha, test_file)`.
- **Treatment:** one smell type at a time, coded positive vs negative from tsDetect at baseline. Keep missing/not-applicable separate; never recode missing as negative.
- **Time order:** covariates and treatment are measured at or before the baseline snapshot. Outcomes are measured strictly after baseline, up to the preregistered follow-up ref/window.
- **Separate analyses:** do not combine distinct smell types into one treatment unless a composite is explicitly justified and preregistered.

## 2. Proposed DAG

The graph below is a conceptual starting graph, not a discovered fact. `U` represents incompletely measured engineering/project quality. `S` is inclusion in the analyzable outcome sample (for example, a successful PIT build); conditioning on `S=1` can create selection bias.

```mermaid
flowchart TD
    P[Project context at baseline\n(domain, age, size, activity, framework)] --> T[Baseline test smell\n(one smell type)]
    P --> Y[Post-baseline outcome]
    X[Test-file characteristics at baseline\n(LOC, assertions, complexity, age)] --> T
    X --> Y
    H[Prior test-file history\n(changes, authorship, ownership)] --> T
    H --> Y
    C[Production-code / module context\n(size, complexity, test-to-code ratio)] --> T
    C --> Y
    U[Unmeasured engineering quality] --> T
    U --> Y
    T --> Y
    P --> S[Outcome observed / included]
    C --> S
    Y --> S
```

Interpretation:

- The arrows into `T` and `Y` represent plausible common causes that could confound the treatment–outcome relationship.
- `T -> Y` is the relationship the study wants to estimate; the arrow is a hypothesis, not a finding.
- `U` warns that residual/unmeasured confounding may remain even after measured adjustment.
- `S` is a selection node. For PIT, build success and report availability may depend on project context and code structure. An analysis restricted to successful builds must report exclusions and assess how selection could distort results.
- The graph is intended for post-baseline outcomes such as later file changes or a defensible file-attributed mutation outcome. Each outcome may require a revised DAG.

## 3. Candidate confounders and operational definitions

All candidate covariates must be measured from the baseline snapshot or a window ending at baseline. Do not use post-treatment values as baseline confounders.

| Candidate | Proposed operational definition | Why it may matter | Current availability / action |
|---|---|---|---|
| Test-file size | Nonblank source lines at baseline (`test_loc`) | Larger files have more opportunity to contain smells and may be more likely to change | Already collected approximately by `discovery.py`; document exact counting rule |
| Assertion volume | Count of recognized assertion-call patterns at baseline (`assert_count`) | Test intent/structure may influence both smell detection and later maintenance | Already collected heuristically; validate framework-specific assertion patterns |
| Test-file complexity | Predeclared complexity metric (e.g. cognitive complexity or a named Java AST metric) | Complex tests may be more smell-prone and harder to maintain | Not currently collected; select one tool/definition before extraction |
| Test-file age | Days from first Git-introduced version of the file to baseline | Older tests may accumulate smells and have different change risk | Not currently collected; implement rename-aware history and define file-origin rule |
| Prior change activity | Number of commits touching the file in a fixed pre-baseline window | Prior instability can predict both smell presence and future changes | Not currently included in current outcome tables; add pre-baseline history separately |
| Prior authorship / ownership | Distinct prior contributors and concentration of contributions in a fixed pre-baseline window | Team structure and ownership may affect test style and maintenance | Not currently collected as a baseline covariate; define identity normalization and privacy-safe aggregation |
| Project age | Days since repository's first commit to baseline | Project maturity can affect both test practices and future activity | Mentioned as placeholder in contract; add only with a reproducible definition |
| Project activity / size | Pre-baseline commit count and/or production LOC in a fixed window/snapshot | Active and large projects differ in smell opportunities and outcome rates | Not yet in dataset; avoid an undefined catch-all “project size” |
| Test-to-production code ratio | Baseline test LOC divided by baseline production LOC, at repository or module level | Testing investment may relate to smell prevalence and outcomes | Not currently collected; specify module mapping and zero-denominator handling |
| Production/module complexity | Named metric for the production counterpart or containing module at baseline | Difficult production code can drive complex tests and later changes | `production_file` mapping is heuristic; validate mapping before use |
| Domain / framework | Predeclared project domain and test framework categories at baseline | Different domains/frameworks impose different testing conventions and tool compatibility | Framework currently heuristic; manual validation needed; domain taxonomy not defined |

The candidate list is deliberately not declared a final “sufficient adjustment set.” The Analyst should draw a smell-specific DAG and select a minimal defensible adjustment set from variables that are genuine common causes, not merely variables correlated with the treatment.

## 4. Variables that must not be adjusted for by default

- **Post-baseline changes, bug-fix proxy counts, and PIT outcomes:** these are outcomes or downstream variables, not baseline confounders.
- **Mediators:** if a variable is caused by the smell after baseline and then affects the outcome, adjusting for it would remove part of the total effect. Decide whether the estimand is total or direct effect before considering mediator adjustment.
- **Colliders / selection variables:** do not automatically adjust for successful build, successful PIT execution, or availability of an outcome. Report the full eligible cohort, failures, and sensitivity to selection.
- **Detector missingness:** a failed/unsupported tsDetect result is not a negative treatment. Report it separately and investigate whether missingness depends on framework/project characteristics.
- **Variables mechanically embedded in a smell definition:** test LOC or assertion count may overlap with some smell rules. For each smell, inspect the detector rule and assess whether adjusting for that metric creates overadjustment, near-deterministic treatment prediction, or positivity problems. Run prespecified sensitivity models rather than assuming it is always safe.

## 5. Outcome-specific cautions

### 5.1 Change-proneness

Define the outcome before analysis (for example, number of post-baseline commits touching the baseline file, or a binary indicator of at least one change). Use a fixed follow-up duration or account for differing observation time. A file change is not automatically a defect fix. Rename tracking and cross-file movement limitations must be reported.

### 5.2 Bug-fix co-change proxy

Commit-message regex matches are only `potential_bugfix_commits`, not verified bug fixes. Do not label this outcome “bugs” or “bug fixes” without manual/independent validation. Define the regex, time window, and validation protocol before testing hypotheses.

### 5.3 PIT mutation outcome

A project-wide mutation score is a project-level measure and must never be copied to each test-file row. A file-level PIT outcome is eligible only if a defensible isolation/attribution procedure is demonstrated, logged, and independently checked. Even a selected test class may not map one-to-one to a test file or capture interactions among tests. If valid attribution cannot be established, analyze PIT at project/module level with a matching unit and a correspondingly redrawn DAG, or omit it from file-level causal claims.

## 6. Proposed analysis strategy (requires preregistration)

1. Specify one smell, one estimand, one primary outcome, one follow-up window, and the eligible population.
2. Freeze baseline SHA and calculate all covariates using only information available at/before that SHA.
3. Describe missingness, detector failures, unsupported frameworks, build failures, and sample exclusions before modeling.
4. Estimate unadjusted and adjusted associations. If using propensity scores, inspect overlap/positivity and balance; do not use PSM as an automatic guarantee of causality.
5. If using DoubleML, state the treatment/outcome learners, cross-fitting strategy, clustering structure, and sample-size rationale. Use repository-aware clustering or multilevel methods because files within a repository are not independent.
6. Conduct sensitivity analysis for unmeasured confounding (`U`), alternate covariate sets, alternate outcome definitions, and selection/build failures.
7. Report effect estimates with uncertainty and assumptions. If assumptions are not credible, describe results as adjusted associations rather than causal effects.

No model is run by this document. The current pilot has two repositories and is an engineering integration pilot, not a representative causal sample.

## 7. Approval checklist

Each team member should review and record a decision in the project issue / meeting notes:

- [ ] Agree on the target population and observation unit.
- [ ] Agree on treatment coding separately for each smell type.
- [ ] Agree on one primary outcome and follow-up window per analysis.
- [ ] Agree on the smell-specific DAG and identify plausible omitted causes.
- [ ] Approve operational definitions and extraction windows for each confounder.
- [ ] Check for mediators, colliders, treatment-definition overlap, missingness, and positivity.
- [ ] Approve the handling of repository clustering and failed builds / PIT selection.
- [ ] Preregister hypotheses, estimand, model, sensitivity analyses, and exclusions.
- [ ] Obtain instructor / supervisor Go-No-Go before causal interpretation.

**Approval status:** pending. No team or instructor approval is implied by inclusion of this document in the repository.
