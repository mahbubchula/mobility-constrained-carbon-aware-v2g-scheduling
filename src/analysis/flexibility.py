from __future__ import annotations

import numpy as np
import pandas as pd


def recompute_flexibility(vehicles: pd.DataFrame, config: dict) -> pd.DataFrame:
    result = vehicles.copy()
    result["required_battery_energy_kwh"] = result["battery_kwh"] * (
        result["target_soc"] - result["arrival_soc"]
    )
    result["minimum_charging_hours"] = result["required_battery_energy_kwh"] / (
        config["eta_ch"] * config["charging_power_kw"]
    )
    result["slack_hours"] = result["connection_hours"] - result["minimum_charging_hours"]
    result["flexibility"] = np.maximum(
        0.0, result["slack_hours"] / result["connection_hours"]
    )
    return result

