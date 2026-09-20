from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else ROOT / "config" / "config.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config["root"] = str(ROOT)
    config["delta_t_hours"] = config["time_step_minutes"] / 60.0
    config["eta_ch"] = float(np.sqrt(config["round_trip_efficiency"]))
    config["eta_dis"] = float(np.sqrt(config["round_trip_efficiency"]))
    return config


def ensure_directories() -> None:
    for relative in (
        "data/raw/nhts",
        "data/raw/caiso",
        "data/interim",
        "data/processed",
        "data/synthetic",
        "results/figures",
        "results/tables",
        "results/sensitivity",
        "results/validation",
        "results/logs",
    ):
        (ROOT / relative).mkdir(parents=True, exist_ok=True)


def setup_logging(name: str = "v2g-carbon") -> logging.Logger:
    ensure_directories()
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    file_handler = logging.FileHandler(ROOT / "results" / "logs" / "pipeline.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(stream)
    logger.addHandler(file_handler)
    return logger


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def dataframe_to_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def weighted_choice_indices(
    rng: np.random.Generator, weights: np.ndarray, size: int
) -> np.ndarray:
    clean = np.asarray(weights, dtype=float)
    clean = np.where(np.isfinite(clean) & (clean > 0), clean, 0.0)
    probabilities = clean / clean.sum() if clean.sum() else None
    return rng.choice(len(clean), size=size, replace=True, p=probabilities)
