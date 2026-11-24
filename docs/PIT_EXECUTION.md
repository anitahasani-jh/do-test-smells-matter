# PIT mutation testing — Experimenter handoff

## What this adds
`tools/pit_runner.py` runs PIT against a Maven checkout pinned to an exact Git SHA, captures the Maven log and PIT XML report, counts mutation statuses, and calculates a transparent mutation score. It does not invent data and does not claim test-level attribution from a project-wide run.

## Prerequisites
- JDK compatible with the target repository (the project's Java source level may require a specific JDK)
- Maven (`mvn`) and a buildable Maven project
- Network access on first run to resolve the PIT Maven plugin/dependencies
- A clean checkout at the baseline SHA used by `smells.csv`

Check:
```powershell
git -C C:\path\to\repo rev-parse HEAD
mvn -version
java -version
```

## Project-level pilot
Run this first to verify PIT works on one small repository:
```powershell
python tools/pit_runner.py `
  --repo C:\path\to\repo `
  --repository-id repo-id `
  --snapshot-sha FULL_BASELINE_SHA `
  --target-classes 'com.example.*' `
  --output results\pit\repo-project.json
```
This run reports a **project-level** score only. Its `attribution_method` is `project_level_only`; it must not be joined to individual test files or presented as a test-class score.

## Isolated test-class run
For a test class whose fully-qualified name maps to one test file:
```powershell
python tools/pit_runner.py `
  --repo C:\path\to\repo `
  --repository-id repo-id `
  --snapshot-sha FULL_BASELINE_SHA `
  --target-classes 'com.example.*' `
  --test-class 'com.example.CalculatorTest' `
  --test-file 'src/test/java/com/example/CalculatorTest.java' `
  --output results\pit\repo-CalculatorTest.json
```
This reruns PIT with only that test class selected. It is recorded as `isolated_test_file`; inspect the Maven log and PIT XML to confirm that the selected test actually ran and that the file-to-class mapping is correct. A string flag is not proof of valid attribution. Do not use this mode when the test file contains multiple classes, helper tests, parameterized suites, or nonstandard test discovery unless the mapping is independently verified.

## Mutation score definition
The runner uses:
`KILLED / (KILLED + SURVIVED + TIMED_OUT + MEMORY_ERROR + RUN_ERROR)`.
`NO_COVERAGE` and `NON_VIABLE` are reported separately and excluded from this denominator. Unknown PIT statuses are retained in `status_counts` and must be reviewed before reporting. This is a documented project operational definition; compare with PIT's own report and state the denominator in the paper.

## Outputs
For each invocation:
- JSON: full status counts, score, pinned SHA, PIT report hash, Maven exit code, log and attribution metadata.
- CSV: one row using `contracts/pit-results.example.csv` columns.
- Maven log and `target/pit-reports/mutations.xml` remain in the target checkout.

Only rows from verified isolated test-file runs can pass the current `team7 validate --pit` contract. Project-level rows are intentionally rejected for file-level causal analysis. If PIT fails or reports zero eligible mutants, the result is not measured; do not convert it to zero.

## Scope and limits
Follow the course brief: choose a manageable subset (about 20–50 small repositories) for mutation testing, not the entire 100–300-repository collection. Start with one pilot, inspect build/test discovery and report, then expand. PIT may require project-specific configuration for multi-module builds, nonstandard source roots, JUnit/TestNG versions, target classes and Java versions. The runner currently assumes a Maven project and one module's default report path; adapt and record deviations before using other build systems.
