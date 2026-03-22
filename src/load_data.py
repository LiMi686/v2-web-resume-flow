"""Helpers for loading lightweight project datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_policy_sources(path: str = "Data/policy_sources.csv") -> pd.DataFrame:
    """Load the policy source table used by the legacy analysis app."""
    return pd.read_csv(Path(path))


if __name__ == "__main__":
    print(load_policy_sources().head())
