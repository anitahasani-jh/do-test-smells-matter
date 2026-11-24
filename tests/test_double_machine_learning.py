import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location('double_machine_learning', Path(__file__).parents[1] / 'tools' / 'double_machine_learning.py')
dml = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dml)


def test_dml_recovers_synthetic_signal():
    rng=np.random.default_rng(12); n=600
    x=rng.normal(size=n); p=1/(1+np.exp(-(.3*x)))
    a=rng.binomial(1,p); y=2.0*a + 1.5*x + rng.normal(scale=1,size=n)
    df=pd.DataFrame({'treat':a,'outcome':y,'x':x})
    audit,preds=dml.run_dml(df,'treat','outcome',['x'],folds=5,seed=4)
    assert abs(audit['estimate']-2.0) < 0.5
    assert len(preds)==n
    assert audit['method']=='partially_linear_DML_cross_fitted'
