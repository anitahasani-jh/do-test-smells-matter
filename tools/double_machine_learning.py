#!/usr/bin/env python3
"""Cross-fitted partially-linear Double Machine Learning (DML) for binary treatment."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.model_selection import KFold, StratifiedKFold


def run_dml(df: pd.DataFrame, treatment: str, outcome: str, covariates: list[str], id_cols: list[str] | None = None, folds: int = 5, seed: int = 7, learner: str = 'random_forest'):
    required = [treatment, outcome, *covariates]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(f'Missing columns: {missing_cols}')
    work = df.copy()
    n_input = len(work)
    work[treatment] = pd.to_numeric(work[treatment], errors='coerce')
    work[outcome] = pd.to_numeric(work[outcome], errors='coerce')
    work = work.dropna(subset=required).copy()
    if not set(work[treatment].unique()).issubset({0, 1}) or work[treatment].nunique() != 2:
        raise ValueError('Treatment must contain both binary values 0 and 1 only.')
    if len(work) < max(30, folds * 4):
        raise ValueError(f'Insufficient complete cases ({len(work)}) for {folds}-fold cross-fitting; need at least {max(30, folds*4)}.')
    A = work[treatment].astype(int).to_numpy()
    Y = work[outcome].astype(float).to_numpy()
    X = work[covariates].copy()
    num_cols = list(X.select_dtypes(include=[np.number]).columns)
    cat_cols = [c for c in covariates if c not in num_cols]
    transformers = []
    if num_cols:
        transformers.append(('num', Pipeline([('impute', SimpleImputer(strategy='median')), ('scale', StandardScaler())]), num_cols))
    if cat_cols:
        transformers.append(('cat', Pipeline([('impute', SimpleImputer(strategy='most_frequent')), ('onehot', OneHotEncoder(handle_unknown='ignore'))]), cat_cols))
    prep = ColumnTransformer(transformers, remainder='drop')
    if learner == 'random_forest':
        model_m = RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=seed, n_jobs=-1)
        model_g = RandomForestClassifier(n_estimators=300, min_samples_leaf=5, random_state=seed, n_jobs=-1, class_weight='balanced')
    else:
        model_m = HistGradientBoostingRegressor(max_iter=150, l2_regularization=1.0, random_state=seed)
        model_g = HistGradientBoostingClassifier(max_iter=150, l2_regularization=1.0, random_state=seed)
    m_hat = np.zeros(len(work)); g_hat = np.zeros(len(work))
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    for train, test in cv.split(X, A):
        prep_y = prep.fit(X.iloc[train])
        Xt, Xv = prep_y.transform(X.iloc[train]), prep_y.transform(X.iloc[test])
        ym = model_m.fit(Xt, Y[train]); m_hat[test] = ym.predict(Xv)
        gm = model_g.fit(Xt, A[train])
        classes = list(gm.classes_)
        g_hat[test] = gm.predict_proba(Xv)[:, classes.index(1)]
    g_hat = np.clip(g_hat, 0.01, 0.99)
    v = A - g_hat
    u = Y - m_hat
    denom = float(np.mean(v * v))
    if denom < 1e-8:
        raise ValueError('Near-zero residual treatment variance; positivity/overlap may be inadequate.')
    theta = float(np.mean(v * u) / denom)
    psi = (v * (u - theta * v)) / denom
    se = float(np.std(psi, ddof=1) / np.sqrt(len(psi)))
    lo, hi = theta - 1.96 * se, theta + 1.96 * se
    audit = {
        'method': 'partially_linear_DML_cross_fitted', 'estimand': 'partially-linear treatment effect under stated assumptions',
        'n_input': n_input, 'n_complete_case': len(work), 'n_excluded_missing': n_input-len(work),
        'n_treated': int(A.sum()), 'n_control': int((1-A).sum()), 'folds': folds, 'seed': seed,
        'learner': learner, 'propensity_min': float(g_hat.min()), 'propensity_max': float(g_hat.max()),
        'propensity_fraction_clipped': float(np.mean((g_hat <= .0100001) | (g_hat >= .9899999))),
        'estimate': theta, 'iid_standard_error': se, 'iid_95ci': [float(lo), float(hi)],
        'warning': 'IID uncertainty is not repository-cluster-robust. Treat inferential interval as provisional for files nested within repositories; implement repository-cluster bootstrap before confirmatory claims.',
        'assumptions': ['no unmeasured confounding given baseline covariates', 'overlap/positivity', 'correct partially-linear structure or sufficiently accurate nuisance learning', 'consistent treatment/outcome definitions', 'no post-treatment covariates'],
    }
    out = pd.DataFrame({'row_index': work.index, 'treatment_observed': A, 'outcome_observed': Y, 'outcome_prediction_oof': m_hat, 'propensity_oof': g_hat, 'treatment_residual': v, 'outcome_residual': u})
    if id_cols:
        for c in id_cols:
            if c in work.columns: out[c] = work[c].to_numpy()
    return audit, out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True); p.add_argument('--output-dir', required=True)
    p.add_argument('--treatment', required=True); p.add_argument('--outcome', required=True)
    p.add_argument('--covariates', required=True, help='Comma-separated pre-treatment covariates')
    p.add_argument('--id-cols', default='repository_id,snapshot_sha,test_file')
    p.add_argument('--folds', type=int, default=5); p.add_argument('--seed', type=int, default=7)
    p.add_argument('--learner', choices=['random_forest','hist_gradient_boosting'], default='random_forest')
    a=p.parse_args(); outdir=Path(a.output_dir); outdir.mkdir(parents=True, exist_ok=True)
    df=pd.read_csv(a.input)
    audit, predictions=run_dml(df,a.treatment,a.outcome,[x.strip() for x in a.covariates.split(',') if x.strip()],[x.strip() for x in a.id_cols.split(',') if x.strip()],a.folds,a.seed,a.learner)
    predictions.to_csv(outdir/'dml_oof_predictions.csv',index=False)
    (outdir/'dml_summary.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps(audit,indent=2))
if __name__=='__main__': main()
