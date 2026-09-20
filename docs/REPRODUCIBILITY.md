# Reproducibility Guide

## Purpose

This guide reproduces the numerical analysis, robustness experiments, figures, tables, and validation evidence. Precomputed outputs are included so that authorized collaborators can inspect the reported results without first rerunning the full year-long workflow.

## Requirements

- Python 3.12
- A platform supported by the packages pinned in `requirements.txt`
- Sufficient memory and storage for EV-level annual schedules
- The HiGHS optimization solver, installed through the Python dependencies

Create the environment with either `environment.yml` or `requirements.txt` as shown in the main README.

## Configuration and determinism

The authoritative experiment settings are in `config/config.yaml`. The released configuration uses random seed `20260821`, a 15-minute resolution, 500 EVs per day, and 365 simulated days. Randomized population construction and bootstrap calculations use controlled seeds.

Hardware, operating-system, solver, and dependency differences may cause very small floating-point variation. They should not change the substantive conclusions or pass/fail consistency checks.

## Execution levels

### 1. Fast verification

```bash
python scripts/run_all.py --quick
python -m pytest -q
```

Use this to verify the environment and the main workflow on a reduced workload.

### 2. Complete primary workflow

```bash
python scripts/run_all.py
```

This processes inputs, constructs the analysis population, executes the charging strategies, aggregates results, and creates the primary tables and figures.

### 3. Extended robustness workflow

```bash
python -m src.analysis.robustness_sensitivity
python -m src.analysis.robustness_tables
python -m src.visualization.fig12_robustness_extensions
```

These commands generate the extended participation, infrastructure, battery-wear, forecast-error, temporal-resolution, and fleet-composition analyses.

### 4. Final verification

```bash
python -m pytest -q
python -m src.validation.final_quality_control
```

The final validator checks the presence and consistency of headline results, robustness artifacts, figures, and tables. Its machine-readable report is written to `results/validation/final_quality_control.csv`.

## Expected headline results

The released configuration reports annual carbon reductions of approximately:

- 26.80 tCO₂ for smart charging relative to uncontrolled charging;
- 13.63 tCO₂ for V2G relative to smart charging; and
- 40.43 tCO₂ for V2G relative to uncontrolled charging.

These values are scenario outputs, not universal causal effects.

## Interpretation limits

The carbon objective uses an average emissions rate signal. The study therefore quantifies accounting-based scenario differences under the stated data and constraints. It does not estimate marginal generator dispatch, distribution-network power flow, market-clearing effects, or causal system-wide emissions.
