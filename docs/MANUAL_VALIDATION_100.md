# Manual validation of 100 tsDetect predictions

## What is being validated

The instructor's Team 7 brief requires running tsDetect on the sampled Java repositories and manually reviewing 100 samples to report detector accuracy. This protocol operationalizes one review unit as:

**one predicted-positive pair: (repository_id, snapshot_sha, test_file, smell_type).**

This is suitable for estimating the positive predictive value / precision of tsDetect's positive detections. It is not a complete estimate of recall or overall accuracy because predicted-negative cases are not sampled in this 100-item positive-only review.

## Critical status rule

The repository does not contain the actual 100 manually adjudicated labels. The workbook created from the script is a blank annotation instrument, not completed ground truth. Never fill labels by guessing from the detector output. Reviewers must inspect the exact pinned source file at `snapshot_sha`, compare it with the operational definition of the smell in tsDetect v2.2 / the original smell catalog, and record evidence.

## Sampling procedure

1. Finish the 100–300 repository collection run.
2. Use `results/<RUN_ID>/smells.csv` and its matching `tests.csv` / manifest.
3. Run:
   `python tools/manual_validation.py --smells results/<RUN_ID>/smells.csv --output results/<RUN_ID>/manual_validation_100.csv --n 100 --seed 7`
4. The script selects up to 100 measured positive detections, stratified as evenly as possible across smell types, with a fixed seed. It fails if fewer than 100 eligible positive predictions exist; it does not duplicate or invent samples.
5. Give the same 100 rows to two reviewers independently. Do not show reviewer 2 reviewer 1's labels.
6. Each reviewer chooses `confirmed`, `not_confirmed`, or `uncertain`, and records a short code-level evidence note. `uncertain` must be adjudicated or reported separately; do not silently count it as true.
7. Resolve disagreements in an adjudication meeting. Preserve both original labels and the adjudicated label.

## Decision rules

- `confirmed`: the source code at the pinned SHA satisfies the exact smell definition.
- `not_confirmed`: the source code does not satisfy the definition; note the reason (e.g., detector parsing/heuristic error, unsupported framework, false positive).
- `uncertain`: source or definition is insufficient to decide; explain why.
- If the file is missing at the pinned SHA or the detector row is invalid/missing, mark the item `uncertain` and retain it; do not replace it silently after review starts.

## Metrics

For the 100 predicted-positive items, after adjudication:

- TP = number adjudicated `confirmed`
- FP = number adjudicated `not_confirmed`
- Unresolved = number adjudicated `uncertain`
- Precision among resolved = TP / (TP + FP)
- Unresolved rate = Unresolved / 100

Report the numerator and denominator, not only a percentage. Example format only: `precision = TP/(TP+FP)`. Do not put example numbers into the paper.

Inter-rater agreement:
- Cohen's kappa between Reviewer 1 and Reviewer 2, computed on rows where both supplied a non-uncertain label.
- Report the number of rows included in kappa and the confusion matrix.
- If there are multiple smell categories and reviewers are labeling the category itself rather than confirming one fixed predicted category, use an appropriate multi-class agreement analysis; this workbook assumes binary confirmation of each predicted smell.

## Limitations

- This design estimates precision for sampled positive predictions, not recall, specificity, or population-wide detector accuracy.
- Stratification across smell types means the unweighted overall precision is not necessarily prevalence-weighted. Report per-smell precision and the sampling method. If an overall estimate is required, compute a weighted estimate using the population counts of positive predictions by smell type.
- A 100-row sample from a convenience sample of repositories does not make the repository sample representative of all Java projects.
- The detector version, JAR SHA-256, source SHA, file path, and review evidence must be retained.

## Files

- `manual_validation_100.csv`: blank 100-row review template.
- `tools/manual_validation.py`: creates a reproducible sample from actual `smells.csv`.
- `tools/summarize_manual_validation.py`: computes precision and Cohen's kappa only after two reviewers and adjudication have entered labels.
- `docs/MANUAL_VALIDATION_100.md`: this protocol.
