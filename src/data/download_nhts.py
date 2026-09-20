from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path

from src.common import ROOT, ensure_directories, load_config, setup_logging


FILES = {
    "nhts_csv": "nhts_2022_v2_1_csv.zip",
    "nhts_codebook_xlsx": "nhts_2022_v2_1_codebook.xlsx",
    "nhts_codebook_pdf": "nhts_2022_v2_1_codebook.pdf",
}


def _download(url: str, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as out:
        shutil.copyfileobj(response, out)
    temporary.replace(destination)


def acquire_nhts(config: dict | None = None) -> list[Path]:
    config = config or load_config()
    ensure_directories()
    logger = setup_logging()
    raw_dir = ROOT / "data" / "raw" / "nhts"
    acquired: list[Path] = []
    for key, filename in FILES.items():
        destination = raw_dir / filename
        if not destination.exists() or destination.stat().st_size == 0:
            logger.info("Downloading NHTS source: %s", filename)
            _download(config["data_urls"][key], destination)
        acquired.append(destination)

    archive = raw_dir / FILES["nhts_csv"]
    expected = {"hhv2pub.csv", "perv2pub.csv", "tripv2pub.csv", "vehv2pub.csv"}
    if not expected.issubset({p.name for p in raw_dir.iterdir()}):
        logger.info("Extracting NHTS public-use CSV files")
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(raw_dir)
    acquired.extend(raw_dir / name for name in sorted(expected))
    return acquired


if __name__ == "__main__":
    acquire_nhts()

