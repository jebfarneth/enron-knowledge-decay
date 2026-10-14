"""Load the functional-importance configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Return functional/config.yaml as a dict, with paths resolved against functional/."""
    with open(path or ROOT / "config.yaml", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config["paths"] = {key: (ROOT / value).resolve() for key, value in config["paths"].items()}
    return config
