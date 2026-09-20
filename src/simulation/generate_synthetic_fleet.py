from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from src.common import ROOT, dataframe_to_parquet, load_config, setup_logging, weighted_choice_indices
from src.simulation.soc_generation import departure_target, sample_home_soc
from src.simulation.vehicle_archetypes import sample_archetypes


def _sample_day(
    day: pd.Timestamp,
    day_number: int,
    calibration: pd.DataFrame,
    config: dict,
    rng: np.random.Generator,
    n_evs: int,
) -> pd.DataFrame:
    weekend = day.dayofweek >= 5
    candidates = calibration.loc[calibration["is_weekend"].eq(weekend)]
    if len(candidates) < 20:  # defensive fallback; not used by the 2022 pool
        candidates = calibration
    sampled_indices = weighted_choice_indices(
        rng, candidates["nhts_weight"].to_numpy(), n_evs
    )
    base = candidates.iloc[sampled_indices].reset_index(drop=True)

    limit = config["time_perturbation_limit_minutes"]
    arrival_noise = np.clip(
        rng.normal(0, config["arrival_perturbation_sd_minutes"], n_evs), -limit, limit
    )
    departure_noise = np.clip(
        rng.normal(0, config["departure_perturbation_sd_minutes"], n_evs), -limit, limit
    )
    arrival = np.clip(base["arrival_min"].to_numpy() + arrival_noise, 0, 1425)
    departure = np.clip(base["departure_min"].to_numpy() + departure_noise, 15, 1440)
    invalid_time = departure <= arrival + 15
    # Preserve the base duration for rare perturbations that invert very short shifts.
    departure[invalid_time] = np.minimum(
        1440,
        arrival[invalid_time]
        + np.maximum(
            15,
            base.loc[invalid_time, "departure_min"].to_numpy()
            - base.loc[invalid_time, "arrival_min"].to_numpy(),
        ),
    )

    sigma = config["distance_log_perturbation_sd"]
    distance_in = base["inbound_distance_km"].to_numpy() * np.exp(rng.normal(0, sigma, n_evs))
    distance_out = base["return_distance_km"].to_numpy() * np.exp(rng.normal(0, sigma, n_evs))

    archetype, battery, base_intensity = sample_archetypes(rng, config, n_evs)
    intensity_multiplier = np.clip(
        rng.normal(1.0, config["energy_intensity_relative_sd"], n_evs), 0.85, 1.15
    )
    energy_intensity = base_intensity * intensity_multiplier
    inbound_energy = distance_in * energy_intensity
    return_energy = distance_out * energy_intensity

    arrival_interval = np.ceil(arrival / config["time_step_minutes"]).astype(int)
    departure_interval = np.floor(departure / config["time_step_minutes"]).astype(int)
    departure_interval = np.minimum(departure_interval, 96)
    n_intervals = departure_interval - arrival_interval
    no_interval = n_intervals <= 0
    if no_interval.any():
        arrival[no_interval] = base.loc[no_interval, "arrival_min"].to_numpy()
        departure[no_interval] = base.loc[no_interval, "departure_min"].to_numpy()
        arrival_interval[no_interval] = np.ceil(
            arrival[no_interval] / config["time_step_minutes"]
        ).astype(int)
        departure_interval[no_interval] = np.floor(
            departure[no_interval] / config["time_step_minutes"]
        ).astype(int)
        n_intervals = departure_interval - arrival_interval

    home_soc = sample_home_soc(rng, config, n_evs)
    arrival_soc = home_soc - inbound_energy / battery
    target = departure_target(arrival_soc, return_energy, battery, config)
    eta_ch = math.sqrt(config["round_trip_efficiency"])
    feasibility_eta_ch = math.sqrt(min(config["efficiency_sensitivity"]))

    # Regenerate only the initial SOC when physical arrival or minimum-power
    # charging feasibility fails, as prescribed. Feasibility at 3.6 kW ensures
    # the charger-power sensitivity uses the identical EV-day fleet.
    unresolved = np.zeros(n_evs, dtype=bool)
    for _ in range(250):
        required_battery = battery * (target - arrival_soc)
        capacity_at_min_power = (
            n_intervals
            * config["delta_t_hours"]
            * config["minimum_sensitivity_power_kw"]
            * feasibility_eta_ch
        )
        target_90 = departure_target(
            arrival_soc, return_energy, battery, config, standard_target=0.90
        )
        required_at_90 = battery * (target_90 - arrival_soc)
        capacity_at_base_power_low_efficiency = (
            n_intervals
            * config["delta_t_hours"]
            * config["charging_power_kw"]
            * feasibility_eta_ch
        )
        infeasible = (
            (arrival_soc < config["soc_min"])
            | (arrival_soc > config["soc_max"])
            | (target > config["soc_max"])
            | (return_energy / battery + config["soc_reserve"] > 0.90)
            | (n_intervals <= 0)
            | (required_battery > capacity_at_min_power + 1e-9)
            | (required_at_90 > capacity_at_base_power_low_efficiency + 1e-9)
        )
        if not infeasible.any():
            break
        home_soc[infeasible] = sample_home_soc(rng, config, int(infeasible.sum()))
        arrival_soc[infeasible] = (
            home_soc[infeasible] - inbound_energy[infeasible] / battery[infeasible]
        )
        target[infeasible] = departure_target(
            arrival_soc[infeasible],
            return_energy[infeasible],
            battery[infeasible],
            config,
        )
    else:
        # Rare combinations of a long commute and very short work session cannot
        # be repaired by resampling SOC alone. Resample those complete EV-day
        # profiles while leaving every feasible draw untouched.
        unresolved = infeasible.copy()

    required_battery = battery * (target - arrival_soc)
    connection_hours = n_intervals * config["delta_t_hours"]
    minimum_charging_hours = required_battery / (eta_ch * config["charging_power_kw"])
    slack_hours = connection_hours - minimum_charging_hours
    flexibility = np.maximum(0, slack_hours / connection_hours)

    result = pd.DataFrame(
        {
            "date": day.normalize(),
            "day_index": day_number,
            "ev_id": np.arange(n_evs, dtype=int),
            "ev_day_id": day_number * n_evs + np.arange(n_evs, dtype=int),
            "source_id": base["source_id"].to_numpy(),
            "is_weekend": weekend,
            "arrival_min": arrival,
            "departure_min": departure,
            "arrival_interval": arrival_interval,
            "departure_interval": departure_interval,
            "connection_hours": connection_hours,
            "inbound_distance_km": distance_in,
            "return_distance_km": distance_out,
            "archetype": archetype,
            "battery_kwh": battery,
            "energy_intensity_kwh_per_km": energy_intensity,
            "inbound_energy_kwh": inbound_energy,
            "return_energy_kwh": return_energy,
            "home_departure_soc": home_soc,
            "arrival_soc": arrival_soc,
            "target_soc": target,
            "required_battery_energy_kwh": required_battery,
            "minimum_charging_hours": minimum_charging_hours,
            "slack_hours": slack_hours,
            "flexibility": flexibility,
        }
    )
    if unresolved.any():
        bad_positions = np.flatnonzero(unresolved)
        replacements = _sample_day(
            day,
            day_number,
            calibration,
            config,
            rng,
            len(bad_positions),
        ).reset_index(drop=True)
        replace_columns = [
            column for column in result.columns if column not in {"ev_id", "ev_day_id"}
        ]
        result.loc[bad_positions, replace_columns] = replacements[replace_columns].to_numpy()
    result["ev_id"] = np.arange(n_evs, dtype=int)
    result["ev_day_id"] = day_number * n_evs + np.arange(n_evs, dtype=int)
    return result


def generate_synthetic_fleet(
    config: dict | None = None,
    n_days: int | None = None,
    n_evs_per_day: int | None = None,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    config = config or load_config()
    logger = setup_logging()
    calibration = pd.read_parquet(
        ROOT / "data" / "processed" / "commuter_calibration_pool.parquet"
    )
    n_days = n_days or config["n_days"]
    n_evs = n_evs_per_day or config["n_evs_per_day"]
    dates = pd.date_range(f"{config['study_year']}-01-01", periods=n_days, freq="D")
    rng = np.random.default_rng(config["seed"])
    parts = [
        _sample_day(day, day_number, calibration, config, rng, n_evs)
        for day_number, day in enumerate(dates)
    ]
    fleet = pd.concat(parts, ignore_index=True)
    destination = (
        Path(output_path)
        if output_path is not None
        else ROOT / "data" / "synthetic" / "synthetic_ev_days.parquet"
    )
    dataframe_to_parquet(fleet, destination)
    logger.info("Generated %d synthetic EV-day profiles", len(fleet))
    return fleet


if __name__ == "__main__":
    generate_synthetic_fleet()
