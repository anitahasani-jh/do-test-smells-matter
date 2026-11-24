# Research and data contract (requires approval of all three team members)

Status: proposal, NOT an approved causal design. A reviewable DAG/confounder proposal is in `DAG_AND_CONFOUNDERS.md`; all three team members and the instructor must approve the smell-specific DAG, hypotheses, estimand, identification assumptions, treatment, outcomes and confounders before causal analysis.

- Observation unit: one Java test FILE at baseline snapshot; a file need not correspond to one class or method. Composite key: repository_id + snapshot_sha + test_file.
- Treatment: each tsDetect boolean smell label, including negative detections. Missing detector result must remain missing.
- Time: treatment measured exclusively on the pinned baseline snapshot. Outcomes are commits strictly after snapshot on its ancestor chain up to followup_ref. If both refs are HEAD, the follow-up is empty; this is a smoke test, NOT a valid outcome sample.
- Rename tracking: follow Git-recognized file renames from the baseline filename, but cross-file moves and unrecognized renames remain a limitation.
- Bugfix proxy: regex matches on commit messages are only potential_bugfix_commits and are NOT verified bug fixes.
- Mutation: PIT execution is Experimenter's task. Project mutation score cannot be labeled test-class mutation score without validated test attribution or isolation.
- Confounders: see `DAG_AND_CONFOUNDERS.md` and `configs/causal_variable_dictionary.csv`. `test_loc`, `assert_count`, and `project_age_days` are not a sufficient adjustment set. Candidate variables require smell-specific review, operational definitions, baseline-only measurement, and team approval. The proposed DAG is not approved or empirically validated.
- Sampling: log selection criteria, search date, exclusions, duplicates, failed builds/detections. Always record immutable snapshot SHA.
- Joins: Experimenter and Analyst join on repository_id, snapshot_sha and test_file; class/method mappings require explicit evidence.
- No causal claims are emitted by this data collector.
