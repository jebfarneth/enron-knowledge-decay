"""Load the search configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Return search/config.yaml as a dict, with paths resolved against search/.

    ENRON_SEARCH_DSN, when set, replaces the configured connection string.
    """
    with open(path or ROOT / "config.yaml", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config["paths"] = {key: (ROOT / value).resolve() for key, value in config["paths"].items()}
    config["database"]["dsn"] = os.environ.get("ENRON_SEARCH_DSN", config["database"]["dsn"])
    return config
