from __future__ import annotations

import numpy as np
from scipy.stats import truncnorm


def sample_home_soc(rng: np.random.Generator, config: dict, size: int) -> np.ndarray:
    mean = config["home_soc_mean"]
    sd = config["home_soc_sd"]
    lower = (config["home_soc_lower"] - mean) / sd
    upper = (config["home_soc_upper"] - mean) / sd
    return truncnorm.rvs(lower, upper, loc=mean, scale=sd, size=size, random_state=rng)


def departure_target(
    arrival_soc: np.ndarray,
    return_energy_kwh: np.ndarray,
    battery_kwh: np.ndarray,
    config: dict,
    standard_target: float | None = None,
) -> np.ndarray:
    standard = config["soc_standard_target"] if standard_target is None else standard_target
    mobility_required = return_energy_kwh / battery_kwh + config["soc_reserve"]
    nominal = np.minimum(0.90, np.maximum(standard, mobility_required))
    # A vehicle already above its nominal target is not forced to waste energy.
    # This makes the target an exact, common minimum across all three strategies.
    return np.maximum(arrival_soc, nominal)

