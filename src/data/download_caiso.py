from __future__ import annotations

import calendar
import shutil
import urllib.request
from pathlib import Path

from src.common import ROOT, ensure_directories, load_config, setup_logging


def _download(url: str, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as out:
        shutil.copyfileobj(response, out)
    temporary.replace(destination)


def acquire_caiso(config: dict | None = None) -> list[Path]:
    config = config or load_config()
    ensure_directories()
    logger = setup_logging()
    raw_dir = ROOT / "data" / "raw" / "caiso"
    template = config["data_urls"]["caiso_template"]
    files: list[Path] = []
    for month_number in range(1, 13):
        month = calendar.month_name[month_number].lower()
        destination = raw_dir / f"average-emissions-rate-report-{month}-2025.xlsx"
        if not destination.exists() or destination.stat().st_size == 0:
            logger.info("Downloading CAISO AER: %s 2025", month.title())
            _download(template.format(month=month), destination)
        files.append(destination)
    return files


if __name__ == "__main__":
    acquire_caiso()

