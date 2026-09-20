import pandas as pd

from src.common import ROOT


def test_synthetic_fleet_is_physical():
    path = ROOT / "data" / "synthetic" / "synthetic_ev_days.parquet"
    if not path.exists():
        return
    fleet = pd.read_parquet(path)
    assert (fleet["arrival_soc"] >= 0.20).all()
    assert (fleet["target_soc"] <= 0.95).all()
    assert (fleet["target_soc"] >= fleet["arrival_soc"]).all()
    assert (fleet["departure_interval"] > fleet["arrival_interval"]).all()

