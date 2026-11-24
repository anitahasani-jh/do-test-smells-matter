# Team 7 — Large-scale GitHub repository sampling (100–300 repositories)

## Purpose and status

This protocol uses the existing `team7_pipeline sample` command. It creates a reproducible *candidate-selection frame*, checks that each selected repository has a baseline commit and a later follow-up commit, pins immutable SHAs, and writes a sampling audit.

**Important:** generating the sample configuration is not the same as running tsDetect/PyDriller on all repositories. It is also not causal evidence. Do not report a target of 100–300 as achieved until the generated audit says `selected == requested`, the collection pipeline completes, and repository/test-file counts are reported from actual outputs.

The repository search is public-only and GitHub-ranked. It is not a probability sample of all Java projects. Search ranking, visibility, stars, API limits, build/test framework compatibility, and eligibility exclusions can bias the sample. Obtain team/professor approval of the inclusion criteria before treating it as the final study sample.

## Recommended staged plan

1. **Dry run: 20 repositories.** Check the date window, API access, commit pinning, clone size, detector stability, and runtime.
2. **Main sample: 100 repositories.** Use the command below only after the dry run is reviewed.
3. **Expansion to 200–300.** Increase only if the team approves the sampling frame and storage/runtime budget. Use a new output filename and new run ID; never overwrite or silently replace the first sample.
4. **Collection:** run the pipeline against the generated JSON config. This is a separate step from sample selection.
5. **Quality review:** inspect exclusions, Java test-file counts, framework distribution, detector failures, and missingness. Keep all exclusions and failures in the audit.

## Eligibility and time window

The default query below asks GitHub for public Java repositories with at least 20 stars, excluding forks and archived repositories. The sampler then verifies that there is a commit at or before each date and that the follow-up commit is ahead of the baseline commit.

The date pair below preserves the project's existing pilot window (2025-01-01 to 2025-07-01). If the instructor approves a different observation window, change both dates *before* sample selection and record the approved rationale. Do not change dates after seeing outcomes.

The sampler does not currently guarantee that a repository contains a usable Java test suite or builds with the selected PIT/tsDetect versions. Those are downstream eligibility/measurement checks and must be recorded, not silently inferred from GitHub's `language` field.

## Windows PowerShell — commands

Open PowerShell in the project root.

```powershell
# 1) Create and activate an isolated environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install the project and dependencies
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

# 3) Confirm Git, Java and Python are available
team7 doctor

# 4) Optional dry run first (creates a separate config and audit)
$env:GITHUB_TOKEN = "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN"
team7 sample `
  --query "topic:testing" `
  --count 20 `
  --baseline-date 2025-01-01 `
  --followup-date 2025-07-01 `
  --seed 7 `
  --min-stars 20 `
  --max-candidates 100 `
  --max-pages 2 `
  --output configs/github-sample-20.json

# 5) Main sample of 100 (use after reviewing the dry-run audit)
team7 sample `
  --query "topic:testing" `
  --count 100 `
  --baseline-date 2025-01-01 `
  --followup-date 2025-07-01 `
  --seed 7 `
  --min-stars 20 `
  --max-candidates 300 `
  --max-pages 3 `
  --output configs/github-sample-100.json

# 6) Run the actual data-collection pipeline after checking the generated config
team7 run --config configs/github-sample-100.json
```

For 200 or 300 repositories, use `--count 200` or `--count 300`, keep `--max-candidates` at least as large as `--count`, and use a new output path such as `configs/github-sample-200.json`. The GitHub Search API has a 1,000-result ceiling per query; this implementation also limits `--max-pages` to 10. A larger candidate pool does not guarantee that the requested number passes date/ancestry checks.

## GitHub token

A token is optional for some public API calls but strongly recommended to reduce unauthenticated rate-limit problems. Create a fine-grained token with no repository write permissions; public read access is sufficient. Keep it in the environment variable only. Never commit the token, paste it into config files, or include it in screenshots/logs. If the API reports a rate limit, stop and rerun later; do not bypass limits.

## Expected outputs

For `github-sample-100`, expect:

- `configs/github-sample-100.json` — selected repositories with immutable baseline and follow-up SHAs
- `configs/github-sample-100.sampling-audit.json` — every evaluated candidate, selected/excluded reason, search query, seed, timestamps, and API request count
- `results/github-sample-100/` — created later by the collection pipeline, not by the sampler

The sample audit must report `requested: 100`, `selected: 100`, and `complete_sample: true` in the CLI output. If fewer than 100 pass, the command exits non-zero and records the smaller count; do not pad the sample with invented repositories or reuse unverified SHAs. Expand the candidate pool or revise eligibility/date criteria only with team approval, then create a fresh sample.

## Quality gates before calling it the study dataset

- [ ] Professor/team approval of query, star threshold, dates, and observation unit
- [ ] Audit says selected count equals requested count
- [ ] Each repository is public, non-fork, non-archived, Java-primary, and has two distinct pinned commits
- [ ] Baseline/follow-up ancestry is verified (`ahead_by >= 1`)
- [ ] Actual clone and pipeline run completed for each selected repository
- [ ] Test-file counts and detector status are measured from the pinned baseline
- [ ] Missing detector outputs remain missing/failed, never converted to `false`
- [ ] Test framework compatibility (especially JUnit 5) is reviewed
- [ ] Raw outputs, versions, SHA-256 JAR hash, runtime, and errors are retained
- [ ] Manual detector validation and inter-rater agreement are completed
- [ ] PIT is run only with a defensible per-test/file attribution method
- [ ] Analyst approves DAG, confounders, estimand, and outcome definition before causal estimation

## What this protocol does not do

It does not clone or analyze 100–300 repositories automatically at sample-generation time; `team7 sample` only creates the dated, pinned sample config. `team7 run` performs the actual collection. It does not implement the causal analysis, establish bug-fix ground truth, or fabricate PIT scores. Those remain separate research tasks.
