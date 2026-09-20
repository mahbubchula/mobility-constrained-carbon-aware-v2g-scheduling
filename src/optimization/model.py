from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd
import pyomo.environ as pyo
from pyomo.contrib.appsi.solvers import Highs
from pyomo.contrib.appsi.base import TerminationCondition


@dataclass
class OptimizationResult:
    ev_metrics: pd.DataFrame
    schedule: pd.DataFrame
    objective_kg: float
    termination: str
    simultaneous_intervals: int


def _solver(config: dict) -> Highs:
    solver = Highs()
    solver.config.stream_solver = False
    solver.config.load_solution = True
    solver.highs_options["primal_feasibility_tolerance"] = config["solver_tolerance"]
    solver.highs_options["dual_feasibility_tolerance"] = config["solver_tolerance"]
    solver.highs_options["threads"] = 1
    return solver


def solve_optimized_day(
    vehicles: pd.DataFrame,
    carbon_intensity: np.ndarray,
    config: dict,
    strategy: str,
    v2g_eligible: set[int] | None = None,
    evaluation_carbon_intensity: np.ndarray | None = None,
) -> OptimizationResult:
    strategy = strategy.lower()
    if strategy not in {"smart", "v2g"}:
        raise ValueError("strategy must be 'smart' or 'v2g'")
    dt = config["delta_t_hours"]
    eta_ch = config["eta_ch"]
    eta_dis = config["eta_dis"]
    charge_limit = config["charging_power_kw"]
    discharge_limit = config["discharging_power_kw"]
    tolerance = config["solver_tolerance"]
    evaluation_ci = (
        np.asarray(carbon_intensity, dtype=float)
        if evaluation_carbon_intensity is None
        else np.asarray(evaluation_carbon_intensity, dtype=float)
    )
    if len(evaluation_ci) != len(carbon_intensity):
        raise ValueError("evaluation_carbon_intensity must match the optimization signal")

    local = vehicles.reset_index(drop=True).copy()
    active_pairs: list[tuple[int, int]] = []
    times_by_ev: dict[int, list[int]] = {}
    active_by_time: dict[int, list[int]] = {t: [] for t in range(96)}
    for i, row in local.iterrows():
        times = list(range(int(row.arrival_interval), int(row.departure_interval)))
        if not times:
            raise RuntimeError(f"No connected interval for EV-day {row.ev_day_id}")
        times_by_ev[i] = times
        active_pairs.extend((i, t) for t in times)
        for t in times:
            active_by_time[t].append(i)

    model = pyo.ConcreteModel(name=f"carbon_aware_{strategy}")
    model.I = pyo.RangeSet(0, len(local) - 1)
    model.X = pyo.Set(dimen=2, initialize=active_pairs, ordered=True)
    model.charge = pyo.Var(model.X, domain=pyo.NonNegativeReals, bounds=(0, charge_limit))
    if strategy == "v2g":
        def dis_bounds(_model: pyo.ConcreteModel, i: int, _t: int) -> tuple[float, float]:
            eligible = v2g_eligible is None or int(local.iloc[i].ev_day_id) in v2g_eligible
            return (0.0, discharge_limit if eligible else 0.0)

        model.discharge = pyo.Var(model.X, domain=pyo.NonNegativeReals, bounds=dis_bounds)
    else:
        model.discharge = pyo.Param(model.X, initialize=0.0, mutable=False)

    def final_energy_rule(m: pyo.ConcreteModel, i: int):
        times = times_by_ev[i]
        return sum(
            dt * (eta_ch * m.charge[i, t] - m.discharge[i, t] / eta_dis)
            for t in times
        ) == float(local.iloc[i].required_battery_energy_kwh)

    model.final_energy = pyo.Constraint(model.I, rule=final_energy_rule)

    if strategy == "v2g":
        prefix_pairs = [(i, k) for i, times in times_by_ev.items() for k in range(len(times))]
        model.P = pyo.Set(dimen=2, initialize=prefix_pairs, ordered=True)

        def prefix_energy(m: pyo.ConcreteModel, i: int, k: int):
            return sum(
                dt * (eta_ch * m.charge[i, t] - m.discharge[i, t] / eta_dis)
                for t in times_by_ev[i][: k + 1]
            )

        def provenance_rule(m: pyo.ConcreteModel, i: int, k: int):
            if config.get("same_session_provenance", True):
                lower = 0.0
            else:
                row = local.iloc[i]
                lower = float(row.battery_kwh * (config["soc_min"] - row.arrival_soc))
            return prefix_energy(m, i, k) >= lower

        def upper_soc_rule(m: pyo.ConcreteModel, i: int, k: int):
            row = local.iloc[i]
            headroom = float(row.battery_kwh * (config["soc_max"] - row.arrival_soc))
            return prefix_energy(m, i, k) <= max(0.0, headroom)

        model.same_session_provenance = pyo.Constraint(model.P, rule=provenance_rule)
        model.soc_upper = pyo.Constraint(model.P, rule=upper_soc_rule)

        def discharge_cap_rule(m: pyo.ConcreteModel, i: int):
            cap = float(
                config["v2g_max_discharge_fraction_capacity"] * local.iloc[i].battery_kwh
            )
            return sum(dt * m.discharge[i, t] for t in times_by_ev[i]) <= cap

        model.discharge_cap = pyo.Constraint(model.I, rule=discharge_cap_rule)

    def fleet_net_power(m: pyo.ConcreteModel, t: int):
        return pyo.quicksum(
            m.charge[i, t] - m.discharge[i, t]
            for i in active_by_time[t]
        )

    def import_limit_rule(m: pyo.ConcreteModel, t: int):
        if not active_by_time[t]:
            return pyo.Constraint.Feasible
        return fleet_net_power(m, t) <= float(import_limit)

    def export_limit_rule(m: pyo.ConcreteModel, t: int):
        if not active_by_time[t]:
            return pyo.Constraint.Feasible
        return fleet_net_power(m, t) >= -float(export_limit)

    def ramp_up_rule(m: pyo.ConcreteModel, t: int):
        if not active_by_time[t] and not active_by_time[t - 1]:
            return pyo.Constraint.Feasible
        return fleet_net_power(m, t) - fleet_net_power(m, t - 1) <= float(ramp_limit)

    def ramp_down_rule(m: pyo.ConcreteModel, t: int):
        if not active_by_time[t] and not active_by_time[t - 1]:
            return pyo.Constraint.Feasible
        return fleet_net_power(m, t - 1) - fleet_net_power(m, t) <= float(ramp_limit)

    import_limit = config.get("fleet_import_limit_kw")
    export_limit = config.get("fleet_export_limit_kw")
    ramp_limit = config.get("fleet_ramp_limit_kw_per_interval")
    if import_limit is not None:
        model.fleet_import_limit = pyo.Constraint(
            range(96), rule=import_limit_rule
        )
    if export_limit is not None:
        model.fleet_export_limit = pyo.Constraint(
            range(96), rule=export_limit_rule
        )
    if ramp_limit is not None:
        model.fleet_ramp_up = pyo.Constraint(
            range(1, 96), rule=ramp_up_rule
        )
        model.fleet_ramp_down = pyo.Constraint(
            range(1, 96), rule=ramp_down_rule
        )

    discharge_penalty = float(config.get("v2g_export_penalty_kg_per_kwh", 0.0))
    model.objective = pyo.Objective(
        expr=sum(
            dt
            * (
                float(carbon_intensity[t]) * model.charge[i, t]
                + (discharge_penalty - float(carbon_intensity[t]))
                * model.discharge[i, t]
            )
            for i, t in active_pairs
        ),
        sense=pyo.minimize,
    )

    results = _solver(config).solve(model)
    termination = str(results.termination_condition)
    if results.termination_condition != TerminationCondition.optimal:
        raise RuntimeError(f"{strategy} optimization failed: {termination}")

    fleet_charge = np.zeros(96, dtype=float)
    fleet_discharge = np.zeros(96, dtype=float)
    ev_accumulator: dict[int, dict[str, float]] = defaultdict(
        lambda: {
            "import_kwh": 0.0,
            "export_kwh": 0.0,
            "carbon_kg": 0.0,
            "charge_carbon_kg": 0.0,
            "discharge_carbon_credit_kg": 0.0,
            "max_prefix_battery_kwh": 0.0,
            "min_prefix_battery_kwh": 0.0,
            "soc_30min_early": np.nan,
            "soc_60min_early": np.nan,
        }
    )
    simultaneous = 0
    prefixes = defaultdict(float)
    for i, t in active_pairs:
        charge = float(pyo.value(model.charge[i, t]))
        discharge = float(pyo.value(model.discharge[i, t]))
        if charge > 1e-6 and discharge > 1e-6:
            simultaneous += 1
        fleet_charge[t] += charge
        fleet_discharge[t] += discharge
        acc = ev_accumulator[i]
        acc["import_kwh"] += charge * dt
        acc["export_kwh"] += discharge * dt
        acc["carbon_kg"] += evaluation_ci[t] * dt * (charge - discharge)
        acc["charge_carbon_kg"] += evaluation_ci[t] * dt * charge
        acc["discharge_carbon_credit_kg"] += evaluation_ci[t] * dt * discharge
        prefixes[i] += dt * (eta_ch * charge - discharge / eta_dis)
        acc["max_prefix_battery_kwh"] = max(acc["max_prefix_battery_kwh"], prefixes[i])
        acc["min_prefix_battery_kwh"] = min(acc["min_prefix_battery_kwh"], prefixes[i])
        row = local.iloc[i]
        if t == int(row.departure_interval) - 3:
            acc["soc_30min_early"] = row.arrival_soc + prefixes[i] / row.battery_kwh
        if t == int(row.departure_interval) - 5:
            acc["soc_60min_early"] = row.arrival_soc + prefixes[i] / row.battery_kwh

    prefix = "sc" if strategy == "smart" else "v2g"
    metric_rows = []
    for i, row in local.iterrows():
        acc = ev_accumulator[i]
        import_kwh = acc["import_kwh"]
        export_kwh = acc["export_kwh"]
        metric_rows.append(
            {
                "ev_day_id": int(row.ev_day_id),
                f"{prefix}_import_kwh": import_kwh,
                f"{prefix}_export_kwh": export_kwh,
                f"{prefix}_net_grid_kwh": import_kwh - export_kwh,
                f"{prefix}_carbon_kg": acc["carbon_kg"],
                f"{prefix}_charge_carbon_kg": acc["charge_carbon_kg"],
                f"{prefix}_discharge_carbon_credit_kg": acc[
                    "discharge_carbon_credit_kg"
                ],
                f"{prefix}_departure_soc": row.arrival_soc
                + prefixes[i] / row.battery_kwh,
                f"{prefix}_v2g_active": export_kwh > 1e-6,
                f"{prefix}_efc": export_kwh / row.battery_kwh,
                f"{prefix}_min_prefix_battery_kwh": acc["min_prefix_battery_kwh"],
                f"{prefix}_max_prefix_battery_kwh": acc["max_prefix_battery_kwh"],
                f"{prefix}_soc_30min_early": (
                    acc["soc_30min_early"]
                    if np.isfinite(acc["soc_30min_early"])
                    else row.arrival_soc
                ),
                f"{prefix}_soc_60min_early": (
                    acc["soc_60min_early"]
                    if np.isfinite(acc["soc_60min_early"])
                    else row.arrival_soc
                ),
            }
        )
    schedule = pd.DataFrame(
        {
            "interval": np.arange(96),
            f"{prefix}_charge_power_kw": fleet_charge,
            f"{prefix}_discharge_power_kw": fleet_discharge,
            f"{prefix}_net_power_kw": fleet_charge - fleet_discharge,
            "carbon_intensity_kg_per_kwh": evaluation_ci,
            "optimization_signal_kg_per_kwh": carbon_intensity,
        }
    )
    return OptimizationResult(
        ev_metrics=pd.DataFrame(metric_rows),
        schedule=schedule,
        objective_kg=float(pyo.value(model.objective)),
        termination=termination,
        simultaneous_intervals=simultaneous,
    )
