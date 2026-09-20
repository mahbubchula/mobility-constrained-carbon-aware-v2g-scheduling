#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common import load_config
from src.data.download_caiso import acquire_caiso
from src.data.download_nhts import acquire_nhts
from src.data.manifest import build_manifest
from src.data.preprocess_caiso import preprocess_caiso
from src.data.preprocess_nhts import build_commuter_pool
from src.simulation.generate_synthetic_fleet import generate_synthetic_fleet
from src.simulation.validate_synthetic_data import validate_synthetic_data


def run_data(config: dict | None = None):
    config = config or load_config()
    acquire_nhts(config)
    acquire_caiso(config)
    build_manifest()
    build_commuter_pool(config)
    preprocess_caiso(config)
    generate_synthetic_fleet(config)
    return validate_synthetic_data(config)


if __name__ == "__main__":
    run_data()

