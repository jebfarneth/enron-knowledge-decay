"""Load the single project configuration file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Return config.yaml as a dict, with paths resolved against the repo root."""
    with open(path or ROOT / "config.yaml", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config["paths"] = {key: ROOT / value for key, value in config["paths"].items()}
    return config
