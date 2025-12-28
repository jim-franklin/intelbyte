from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIR = Path(__file__).resolve().parent
OUT_STATE = DATA_DIR / "current_machine_state.csv"
OUT_WO = DATA_DIR / "work_orders.csv"


@dataclass(frozen=True)
class Plant:
    plant_id: int
    plant_name: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def pick_status(
    health: float,
    open_work_orders: int,
    fault_code_id: int | None
) -> str:
    if open_work_orders > 0:
        return "UnderMaintenance"
    if fault_code_id is not None:
        return "Fault"
    if health >= 80:
        return "Running"
    if health >= 55:
        return "Idle"
    return "Idle"


def main(
    seed: int = 7,
    n_plants: int = 2,
    lines_per_plant: int = 10,
    machines_per_line: int = 20,
) -> None:
    rng = np.random.default_rng(seed)
    random.seed(seed)

    plants = [
        Plant(1, "Plant A"),
        Plant(2, "Plant B"),
    ][:n_plants]

    machine_types = ["CNC", "Conveyor", "Press", "Pump"]
    statuses = ["Running", "Idle", "Fault", "UnderMaintenance"]
    issue_types = [
        "HighTemp",
        "HighVibration",
        "ThroughputDrop",
    ]

    now = utc_now()

    rows_state: list[dict] = []
    rows_work_orders: list[dict] = []

    machine_id = 1001
    telemetry_event_id = 50001
    operator_report_id = 90001
    work_order_id = 70001

    for p in plants:
        for li in range(1, lines_per_plant + 1):
            line_id = int(f"{p.plant_id}{li:02d}")
            line_name = f"Line {li}"

            for _ in range(machines_per_line):
                machine_type = random.choice(machine_types)

                # Simulate timestamps
                last_update_at = now - timedelta(minutes=int(rng.integers(0, 180)))
                last_telemetry_at = last_update_at - timedelta(
                    minutes=int(rng.integers(0, 10))
                )

                # Simulate base health score
                health_score = float(np.clip(rng.normal(78, 18), 0, 100))

                # Simulate work orders (maintenance) first so health can depend on it
                open_work_order_count = int(rng.choice([0, 0, 0, 1, 2]))

                # Simulate faults
                has_fault = rng.random() < 0.18
                fault_code_id = int(rng.integers(100, 140)) if has_fault else None

                # Make health consistent with fault/maintenance states
                # - If a machine has an active fault, it should not look perfectly healthy.
                # - If a machine is under maintenance (open work orders), it often has reduced health.
                if fault_code_id is not None:
                    # Bias downward and cap the health to avoid 100 with a fault.
                    # Typical faulty range: 0–70
                    health_score = float(min(health_score, rng.uniform(10, 70)))
                elif open_work_order_count > 0:
                    # Under maintenance, health can vary but should not be perfect.
                    # Typical maintenance range: 30–85
                    health_score = float(min(health_score, rng.uniform(30, 85)))

                # Round after adjustments
                health_score = float(np.clip(health_score, 0, 100))
                last_work_order_id = None
                last_work_order_created_by_type = None
                last_work_order_created_by_id = None
                last_work_order_change_at = None

                if open_work_order_count > 0:
                    # Create 1 open work order record for the queue view.
                    created_by_type = rng.choice(["User", "RuleEngine"], p=[0.6, 0.4])
                    created_by_id = (
                        int(rng.integers(2000, 2050))
                        if created_by_type == "User"
                        else int(rng.integers(300, 330))
                    )
                    wo_created_at = last_update_at - timedelta(
                        minutes=int(rng.integers(5, 90))
                    )

                    last_work_order_id = work_order_id
                    last_work_order_created_by_type = created_by_type
                    last_work_order_created_by_id = created_by_id
                    last_work_order_change_at = wo_created_at

                    rows_work_orders.append(
                        {
                            "workOrderId": work_order_id,
                            "machineId": machine_id,
                            "plantId": p.plant_id,
                            "plantName": p.plant_name,
                            "lineId": line_id,
                            "lineName": line_name,
                            "status": "Open",
                            "createdAt": wo_created_at.strftime("%Y-%m-%d %H:%M"),
                            "closedAt": None,
                            "createdByType": created_by_type,
                            "createdById": created_by_id,
                            "issueType": rng.choice(issue_types),
                        }
                    )
                    work_order_id += 1

                # Simulate operator override occasionally
                status_override = None
                last_operator_report_id = None
                last_override_at = None
                if rng.random() < 0.22:
                    status_override = rng.choice(["Running", "Idle", "Fault"])
                    last_operator_report_id = operator_report_id
                    last_override_at = last_update_at - timedelta(
                        minutes=int(rng.integers(0, 240))
                    )
                    operator_report_id += 1

                # Resolved status using your precedence
                resolved_status = pick_status(
                    health_score, open_work_order_count, fault_code_id
                )
                if status_override is not None and last_override_at is not None:
                    # If override is within last 4 hours, it wins unless under maintenance
                    if resolved_status != "UnderMaintenance" and (
                        now - last_override_at
                    ) <= timedelta(hours=4):
                        resolved_status = status_override

                # Enforce consistency between resolvedStatus and the generated fields.
                # If the final resolved status is Fault, ensure we have a fault code
                # and ensure the health score is not perfectly healthy.
                if resolved_status == "Fault":
                    if fault_code_id is None:
                        fault_code_id = int(rng.integers(100, 140))
                    # Faulty machines should not have 100 health.
                    health_score = float(min(health_score, rng.uniform(10, 70)))
                    health_score = float(np.clip(health_score, 0, 100))

                # If the final resolved status is UnderMaintenance, ensure the state reflects it.
                if resolved_status == "UnderMaintenance":
                    if open_work_order_count == 0:
                        open_work_order_count = 1
                    # Under maintenance should not look perfectly healthy.
                    health_score = float(min(health_score, rng.uniform(30, 85)))
                    health_score = float(np.clip(health_score, 0, 100))

                rows_state.append(
                    {
                        # Location and hierarchy (for filtering and grouping)
                        "plantId": p.plant_id,
                        "plantName": p.plant_name,
                        "lineId": line_id,
                        "lineName": line_name,
                        "machineType": machine_type,
                        # CurrentMachineState core
                        "machineId": machine_id,
                        "resolvedStatus": resolved_status,
                        "healthScore": round(health_score, 2),
                        "openWorkOrderCount": open_work_order_count,
                        "lastUpdateAt": last_update_at.strftime("%Y-%m-%d %H:%M"),
                        # Latest pointers and event context (from your upsert)
                        "lastTelemetryEventId": telemetry_event_id,
                        "lastTelemetryAt": last_telemetry_at.strftime("%Y-%m-%d %H:%M"),
                        "statusRaw": rng.choice(statuses),
                        "faultCodeId": fault_code_id,
                        "lastOperatorReportId": last_operator_report_id,
                        "lastOverrideAt": (
                            last_override_at.strftime("%Y-%m-%d %H:%M") if last_override_at else None
                        ),
                        "statusOverride": status_override,
                        "lastWorkOrderId": last_work_order_id,
                        "lastWorkOrderCreatedByType": last_work_order_created_by_type,
                        "lastWorkOrderCreatedById": last_work_order_created_by_id,
                        "lastWorkOrderChangeAt": (
                            last_work_order_change_at.strftime("%Y-%m-%d %H:%M")
                            if last_work_order_change_at
                            else None
                        ),
                    }
                )

                machine_id += 1
                telemetry_event_id += 1

    df_state = pd.DataFrame(rows_state)
    df_wo = pd.DataFrame(rows_work_orders)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df_state.to_csv(OUT_STATE, index=False)
    df_wo.to_csv(OUT_WO, index=False)

    print(f"Wrote {OUT_STATE} with {len(df_state)} rows")
    print(f"Wrote {OUT_WO} with {len(df_wo)} rows")


if __name__ == "__main__":
    main()
