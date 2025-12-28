from __future__ import annotations

from pathlib import Path

import pandas as pd

from .utils import parse_dt


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_current_state() -> pd.DataFrame:
    path = DATA_DIR / "current_machine_state.csv"
    df = pd.read_csv(path)

    # Parse datetimes
    for col in [
        "lastUpdateAt",
        "lastTelemetryAt",
        "lastOverrideAt",
        "lastWorkOrderChangeAt",
    ]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: parse_dt(x) if pd.notna(x) else None)

    # Ensure types
    for col in ["machineId", "plantId", "lineId", "openWorkOrderCount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    if "healthScore" in df.columns:
        df["healthScore"] = pd.to_numeric(df["healthScore"], errors="coerce")

    return df


def load_work_orders() -> pd.DataFrame:
    path = DATA_DIR / "work_orders.csv"
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)
    for col in ["createdAt", "closedAt"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: parse_dt(x) if pd.notna(x) and x != "" else None)

    return df