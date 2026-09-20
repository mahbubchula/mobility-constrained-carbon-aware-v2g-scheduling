#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.make_all_outputs import make_all_outputs
from scripts.run_data import run_data
from scripts.run_main_analysis import run_main
from src.analysis.sensitivity import run_sensitivity_analysis
from src.common import load_config, setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the complete V2G carbon study")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Smoke-test three days and reduced bootstrap/resampling counts",
    )
    parser.add_argument(
        "--skip-sensitivity",
        action="store_true",
        help="Skip sensitivity (intended only for development diagnostics)",
    )
    args = parser.parse_args()
    config = load_config()
    if args.quick:
        config = copy.deepcopy(config)
        config["bootstrap_repetitions"] = 200
        config["participation_repetitions"] = 10
        config["n_workers"] = 2
    logger = setup_logging()
    logger.info("Phase 1-5: acquire, preprocess, generate, and validate data")
    validation, _ = run_data(config)
    if not validation["acceptable"].all():
        raise RuntimeError("Synthetic mobility validation failed; optimization was not started")
    max_days = 3 if args.quick else None
    logger.info("Phase 6-11: main optimization, tests, bootstrap, and subgroups")
    run_main(config, max_days=max_days)
    if not args.skip_sensitivity:
        logger.info("Phase 12: focused sensitivity analysis")
        run_sensitivity_analysis(config, max_days=max_days)
        logger.info("Phase 13-18: figures, tables, summary, and quality control")
        make_all_outputs()
    logger.info("Pipeline complete")


if __name__ == "__main__":
    main()
