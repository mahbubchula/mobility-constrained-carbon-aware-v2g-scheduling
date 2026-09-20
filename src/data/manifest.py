from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from src.common import ROOT, sha256


def build_manifest() -> pd.DataFrame:
    entries: list[dict] = []
    for path in sorted((ROOT / "data" / "raw" / "nhts").glob("*")):
        if not path.is_file() or path.name == "manifest.csv":
            continue
        entries.append(
            {
                "source_name": "FHWA 2022 NextGen NHTS V2.1",
                "filename": str(path.relative_to(ROOT)),
                "download_date": date.today().isoformat(),
                "coverage_period": "2022 survey",
                "file_size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    for path in sorted((ROOT / "data" / "raw" / "caiso").glob("*.xlsx")):
        entries.append(
            {
                "source_name": "California ISO Average Emissions Rate",
                "filename": str(path.relative_to(ROOT)),
                "download_date": date.today().isoformat(),
                "coverage_period": path.stem.rsplit("-", 2)[-2].title() + " 2025",
                "file_size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    result = pd.DataFrame(entries)
    result.to_csv(ROOT / "data" / "raw" / "manifest.csv", index=False)
    return result


if __name__ == "__main__":
    build_manifest()

