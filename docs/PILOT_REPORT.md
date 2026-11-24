# Exploratory Real-Data Pilot Report

## 1. Study scope
This report documents an exploratory pilot for Do Test Smells Matter? A Causal Study. The pilot uses two Java repositories and 12 baseline test files. It is descriptive and does not establish causal effects.

## 2. Repositories
- qala-io_java-course: 11 test files; baseline a747bb4e; follow-up f0b8b275.
- shankybnl_MobileAutomationFramework: 1 test file; baseline 64597407; follow-up a4443405.
- Both repository statuses: complete_with_na.

## 3. Test smell measurements
- Total smell rows: 252 (21 smell types across 12 test files).
- Measured rows: 242; not_applicable rows: 10.
- Positive detections: 9; negative detections: 233.
- Positive detections: Magic Number Test = 5; Eager Test = 2; Exception Catching Throwing = 1; Unknown Test = 1.
- Eager Test: 5 not_applicable; Lazy Test: 5 not_applicable. All other smell categories had 12 measured rows each.
- Positive rate among measured rows: 9/242 = 3.72 percent.

## 4. Follow-up outcomes
- Outcome rows: 12; all 12 have followup_observed=True.
- change_commits = 0 for all 12 test files.
- potential_bugfix_commits = 0 for all 12 test files.
- Repository-wide follow-up commits: 1 for qala-io_java-course and 2 for MobileAutomationFramework.

## 5. Manual Git verification
- qala-io_java-course: commit f0b8b27 changed only pom.xml (Spring dependency update).
- MobileAutomationFramework: commit a444340 changed README.md; commit 70110d4 added UIAutomation/images/Core_Architecture.png.
- None of these three commits changed a test file. This supports the observed zero test-file changes in this pilot window.

## 6. Validation and tooling
- team7 validate --results results/pilot-2-repos returned valid=true.
- Validation counts: 12 baseline tests, 252 smell rows, 242 measured rows, 12 outcomes, 2 repositories.
- Validation confirms syntax and joins only. It does not establish causal identification, sampling validity, tsDetect accuracy, or PIT correctness.
- PIT was not included in this pilot validation (pit=null).

## 7. Limitations
- The initial requested sample was 20 repositories; only 12 were selected before GitHub API limitations, and only 2 were usable in this pilot subset.
- The pilot contains only 12 test files from 2 repositories and is not representative.
- There is no variation in the primary observed outcome change_commits; therefore, comparative outcome analysis and causal effect estimation are not justified.
- Commit-message bug-fix counts are proxies, not verified defects.
- The 10 not_applicable smell rows must remain distinct from negative detections.
- Potential confounders and the causal DAG have not been approved by the team and instructor.

## 8. Conclusion
The pipeline produced a structurally valid exploratory dataset and the manual Git checks are consistent with the zero test-file-change outcomes. The pilot is useful for checking the workflow and documenting measurement behavior, but it cannot answer whether test smells cause later test-file changes. A larger, better-validated sample with variation in follow-up outcomes is required before causal analysis with DoWhy.

## 9. Reproducibility files
The filtered pilot data are in results/pilot-2-repos/. The original sample data in results/github-sample-20/ were preserved. No synthetic outcomes were added and no causal estimates were fabricated.
