#!/usr/bin/env python3
"""E-value sensitivity analysis for risk-ratio estimates (not generic DML coefficients)."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path


def e_value_rr(rr: float) -> float:
    """Minimum equal-strength RR associations needed to explain away an RR."""
    if not math.isfinite(rr) or rr <= 0:
        raise ValueError('Risk ratio must be a finite positive number.')
    rr = max(rr, 1.0 / rr)  # orient protective effects below 1 toward the null
    if math.isclose(rr, 1.0):
        return 1.0
    return rr + math.sqrt(rr * (rr - 1.0))


def bias_factor(rr_ua: float, rr_ay: float) -> float:
    """Maximum confounding bias factor for positive RR-scale associations."""
    if not all(math.isfinite(x) and x >= 1 for x in (rr_ua, rr_ay)):
        raise ValueError('RR_UA and RR_AY must be finite values >= 1.')
    return (rr_ua * rr_ay) / (rr_ua + rr_ay - 1.0)


def analyze(rr: float, ci_lower: float | None = None, ci_upper: float | None = None,
            rr_ua: float | None = None, rr_ay: float | None = None) -> dict:
    result = {
        'method': 'E-value sensitivity analysis',
        'effect_measure': 'risk_ratio',
        'risk_ratio': rr,
        'e_value_point_estimate': e_value_rr(rr),
        'interpretation': ('Minimum equal-strength risk-ratio associations of an unmeasured confounder '
                           'with treatment and outcome, conditional on measured covariates, required '
                           'to explain away the point estimate.'),
        'warning': ('E-values are not directly applicable to a continuous-outcome DML coefficient, '
                    'an odds ratio without a justified conversion, a mutation score, or an arbitrary '
                    'regression coefficient. Use a risk-ratio estimate and a compatible confidence interval.'),
    }
    if (ci_lower is None) != (ci_upper is None):
        raise ValueError('Provide both CI limits or neither.')
    if ci_lower is not None:
        if ci_lower <= 0 or ci_upper <= 0 or ci_lower > ci_upper:
            raise ValueError('CI limits must be positive and lower <= upper.')
        result['confidence_interval'] = [ci_lower, ci_upper]
        # The CI limit closest to the null (RR=1) determines the CI E-value.
        closest = ci_lower if rr >= 1 else ci_upper
        result['e_value_ci'] = 1.0 if ci_lower <= 1 <= ci_upper else e_value_rr(closest)
        result['ci_includes_null'] = bool(ci_lower <= 1 <= ci_upper)
    if (rr_ua is None) != (rr_ay is None):
        raise ValueError('Provide both RR_UA and RR_AY or neither.')
    if rr_ua is not None:
        bf = bias_factor(rr_ua, rr_ay)
        result['unmeasured_confounder_scenario'] = {
            'rr_unmeasured_treatment': rr_ua,
            'rr_unmeasured_outcome': rr_ay,
            'bias_factor_upper_bound': bf,
            'scenario_explains_point_estimate': bf >= max(rr, 1/rr),
        }
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rr', type=float, required=True, help='Adjusted risk ratio (not odds ratio or DML coefficient)')
    p.add_argument('--ci-lower', type=float)
    p.add_argument('--ci-upper', type=float)
    p.add_argument('--rr-ua', type=float, help='Sensitivity scenario: confounder-treatment RR association, >=1')
    p.add_argument('--rr-ay', type=float, help='Sensitivity scenario: confounder-outcome RR association, >=1')
    p.add_argument('--output', help='Optional JSON output path')
    a = p.parse_args()
    result = analyze(a.rr, a.ci_lower, a.ci_upper, a.rr_ua, a.rr_ay)
    rendered = json.dumps(result, indent=2)
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(rendered + '\n', encoding='utf-8')
    print(rendered)

if __name__ == '__main__':
    main()
