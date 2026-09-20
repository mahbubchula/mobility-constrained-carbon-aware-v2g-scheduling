from __future__ import annotations

import numpy as np
import pandas as pd


def solve_uncontrolled_day(
    vehicles: pd.DataFrame, carbon_intensity: np.ndarray, config: dict
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dt = config["delta_t_hours"]
    eta_ch = config["eta_ch"]
    power_limit = config["charging_power_kw"]
    fleet_power = np.zeros(96, dtype=float)
    rows: list[dict] = []
    for row in vehicles.itertuples(index=False):
        remaining_grid_energy = row.required_battery_energy_kwh / eta_ch
        imported = 0.0
        carbon = 0.0
        for interval in range(row.arrival_interval, row.departure_interval):
            if remaining_grid_energy <= 1e-10:
                break
            power = min(power_limit, remaining_grid_energy / dt)
            interval_energy = power * dt
            fleet_power[interval] += power
            imported += interval_energy
            carbon += interval_energy * carbon_intensity[interval]
            remaining_grid_energy -= interval_energy
        if remaining_grid_energy > 1e-6:
            raise RuntimeError(f"Uncontrolled charging infeasible for EV-day {row.ev_day_id}")
        rows.append(
            {
                "ev_day_id": row.ev_day_id,
                "uc_import_kwh": imported,
                "uc_export_kwh": 0.0,
                "uc_net_grid_kwh": imported,
                "uc_carbon_kg": carbon,
                "uc_charge_carbon_kg": carbon,
                "uc_discharge_carbon_credit_kg": 0.0,
                "uc_departure_soc": row.target_soc,
            }
        )
    schedule = pd.DataFrame(
        {
            "interval": np.arange(96),
            "uc_net_power_kw": fleet_power,
            "carbon_intensity_kg_per_kwh": carbon_intensity,
        }
    )
    return pd.DataFrame(rows), schedule
