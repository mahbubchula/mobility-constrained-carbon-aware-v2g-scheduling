from __future__ import annotations

import numpy as np
import pandas as pd


def add_carbon_opportunity(
    vehicles: pd.DataFrame, carbon_intensity: np.ndarray
) -> pd.DataFrame:
    result = vehicles.copy()
    minima = []
    maxima = []
    for row in result.itertuples(index=False):
        window = carbon_intensity[int(row.arrival_interval) : int(row.departure_interval)]
        minima.append(float(window.min()))
        maxima.append(float(window.max()))
    result["window_ci_min_kg_per_kwh"] = minima
    result["window_ci_max_kg_per_kwh"] = maxima
    result["carbon_opportunity_kg_per_kwh"] = result["window_ci_max_kg_per_kwh"] - result[
        "window_ci_min_kg_per_kwh"
    ]
    return result

