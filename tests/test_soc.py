from src.common import ROOT, load_config
from src.validation.validate_soc import soc_validation
import pandas as pd


def test_saved_soc_results():
    path = ROOT / "results" / "results_ev_level.parquet"
    if not path.exists():
        return
    assert soc_validation(pd.read_parquet(path), load_config()["solver_tolerance"] * 20)["pass"]

