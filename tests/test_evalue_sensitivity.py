import math
import pytest
from tools.evalue_sensitivity import analyze, bias_factor, e_value_rr


def test_e_value_null_and_direction_symmetry():
    assert e_value_rr(1.0) == 1.0
    assert e_value_rr(2.0) == pytest.approx(e_value_rr(0.5))


def test_e_value_known_rr():
    assert e_value_rr(2.0) == pytest.approx(3.41421356237)


def test_ci_crossing_null_has_ci_evalue_one():
    out = analyze(1.8, 0.8, 2.5)
    assert out['e_value_ci'] == 1.0
    assert out['ci_includes_null'] is True


def test_ci_away_from_null():
    out = analyze(2.0, 1.2, 3.0)
    assert out['e_value_ci'] == pytest.approx(e_value_rr(1.2))


def test_bias_factor_scenario():
    assert bias_factor(2, 2) == pytest.approx(4/3)
    out = analyze(1.5, rr_ua=2, rr_ay=2)
    assert out['unmeasured_confounder_scenario']['scenario_explains_point_estimate'] is False


def test_invalid_rr_rejected():
    with pytest.raises(ValueError):
        e_value_rr(0)
