"""Where the desk keeps its data.

The corpus caches and the SQLite index are large and are rebuilt locally, so
they live outside version control: by default in ``<repo>/data``, or wherever
the ``DESK_DATA`` environment variable points.
"""
from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent


def data_dir() -> Path:
    return Path(os.environ.get("DESK_DATA", REPO_ROOT / "data"))


def index_path() -> Path:
    return Path(os.environ.get("DESK_INDEX", data_dir() / "index.sqlite"))


def etymology_path() -> Path:
    return Path(os.environ.get("DESK_ETYMOLOGY", data_dir() / "etymology.sqlite"))


def watchlist_path() -> Path:
    return Path(os.environ.get("DESK_WATCHLIST", REPO_ROOT / "watchlist.yaml"))


def baseline_path() -> Path:
    return REPO_ROOT / "samples" / "baseline.md"
