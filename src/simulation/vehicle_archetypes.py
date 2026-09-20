from __future__ import annotations

import numpy as np


def sample_archetypes(
    rng: np.random.Generator, config: dict, size: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    definitions = config["vehicle_archetypes"]
    names = np.array(list(definitions))
    probabilities = np.array([definitions[name]["share"] for name in names], dtype=float)
    probabilities /= probabilities.sum()
    sampled = rng.choice(names, size=size, p=probabilities)
    battery = np.array([definitions[name]["battery_kwh"] for name in sampled], dtype=float)
    intensity = np.array(
        [definitions[name]["energy_kwh_per_km"] for name in sampled], dtype=float
    )
    return sampled, battery, intensity

