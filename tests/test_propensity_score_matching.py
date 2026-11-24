import pandas as pd

from tools.propensity_score_matching import run_psm


def test_psm_creates_pairs_and_balance_files(tmp_path):
    rows = []
    # Synthetic test fixture only; it is not empirical project evidence.
    for i in range(60):
        treatment = 1 if (i % 10) in (0, 1, 2, 3, 6) else 0
        rows.append({
            "repository_id": f"repo-{i % 3}",
            "snapshot_sha": f"sha-{i}",
            "test_file": f"T{i}.java",
            "smell_present": treatment,
            "post_change_count": (i % 7) + treatment,
            "test_loc": 20 + (i % 10),
            "assert_count": 2 + (i % 5),
        })
    source = tmp_path / "input.csv"
    pd.DataFrame(rows).to_csv(source, index=False)
    result = run_psm(source, tmp_path / "out", "smell_present", "post_change_count",
                     ["test_loc", "assert_count"],
                     ["repository_id", "snapshot_sha", "test_file"], [], 0.2)
    assert result["matched_pairs"] > 0
    assert (tmp_path / "out" / "psm_matched_pairs.csv").exists()
    assert (tmp_path / "out" / "psm_balance.csv").exists()
    assert (tmp_path / "out" / "psm_summary.json").exists()
