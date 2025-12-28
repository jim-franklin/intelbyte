from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import dash_bootstrap_components as dbc
from dash import Input, Output, html, ctx

from .charts import status_pie_chart
from .utils import ago


_NUMERIC_COLS = {
    "plantId",
    "lineId",
    "machineId",
    "healthScore",
    "openWorkOrderCount",
    "faultCodeId",
    "lastTelemetryEventId",
    "lastOperatorReportId",
    "lastWorkOrderId",
    "lastWorkOrderCreatedById",
    "workOrderId",
    "createdById",
}

# Match Altair / Vega-Lite categorical defaults (Tableau 10 first 4)
# Used for KPI card backgrounds to stay consistent with the pie chart.
STATUS_CARD_COLORS: dict[str, str] = {
    "Running": "#4E79A7",  # blue
    "Idle": "#F28E2B",  # orange
    "Fault": "#E15759",  # red
    "UnderMaintenance": "#76B7B2",  # teal
}

OTHER_CARD_COLORS: dict[str, str] = {
    "Machines": "#6C757D",  # bootstrap secondary-ish
    "Average health": "#59A14F",  # green
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _datatable_columns(df: pd.DataFrame) -> list[dict]:
    """
    Build Dash DataTable columns with proper types.

    Your data often becomes object dtype due to NaNs, so we force known numeric columns.
    """
    cols: list[dict] = []
    for c in df.columns:
        col_def = {"name": c, "id": c}

        if c in _NUMERIC_COLS or pd.api.types.is_numeric_dtype(df[c]):
            col_def["type"] = "numeric"
        else:
            col_def["type"] = "text"

        cols.append(col_def)
    return cols


def apply_filters(
    df: pd.DataFrame,
    plants: list[int] | None,
    lines: list[int | str] | None,
    statuses: list[str] | None,
    health_rng: list[int],
    stale_only: bool,
) -> pd.DataFrame:
    out = df.copy()

    # Plant filter (multi)
    if plants and "plantId" in out.columns:
        plant_ids = [int(p) for p in plants if p is not None]
        if plant_ids:
            out = out[out["plantId"].astype("Int64").isin(plant_ids)]

    # Line filter (multi)
    # - If line values are ints, treat as lineId filtering.
    # - If line values are strings, treat as lineName filtering.
    if lines:
        line_ids: list[int] = []
        line_names: list[str] = []
        for v in lines:
            if v is None:
                continue
            if isinstance(v, (int, float)) and "lineId" in out.columns:
                line_ids.append(int(v))
            else:
                line_names.append(str(v))

        if line_ids and "lineId" in out.columns:
            out = out[out["lineId"].astype("Int64").isin(line_ids)]
        if line_names and "lineName" in out.columns:
            out = out[out["lineName"].astype(str).isin(line_names)]

    # Status filter (multi)
    if statuses and "resolvedStatus" in out.columns:
        out = out[out["resolvedStatus"].isin(statuses)]

    # Health range
    if health_rng and "healthScore" in out.columns:
        lo, hi = health_rng
        out = out[(out["healthScore"] >= lo) & (out["healthScore"] <= hi)]

    # Stale only
    if stale_only and "lastUpdateAt" in out.columns:
        cutoff = _now_utc() - timedelta(minutes=30)
        ts = pd.to_datetime(out["lastUpdateAt"], utc=True, errors="coerce")
        out = out[ts.notna() & (ts < cutoff)]

    return out


def make_kpi_cards(df: pd.DataFrame) -> html.Div:
    total = len(df)

    fault = int((df["resolvedStatus"] == "Fault").sum()) if "resolvedStatus" in df.columns else 0
    maint = int((df["resolvedStatus"] == "UnderMaintenance").sum()) if "resolvedStatus" in df.columns else 0
    running = int((df["resolvedStatus"] == "Running").sum()) if "resolvedStatus" in df.columns else 0
    idle = int((df["resolvedStatus"] == "Idle").sum()) if "resolvedStatus" in df.columns else 0

    avg_health = (
        float(df["healthScore"].mean())
        if "healthScore" in df.columns and total > 0
        else 0.0
    )

    def _card(title: str, value: str, bg: str, fg: str = "white"):
        return dbc.Card(
            dbc.CardBody(
                [
                    html.Div(title, style={"opacity": 0.9}),
                    html.H3(value, style={"margin": 0}),
                ]
            ),
            style={
                "backgroundColor": bg,
                "color": fg,
                "border": "0",
                "boxShadow": "0 1px 2px rgba(0,0,0,0.06)",
            },
        )

    cards = dbc.Row(
        [
            dbc.Col(
                _card(
                    "Machines",
                    f"{total}",
                    OTHER_CARD_COLORS["Machines"],
                )
            ),
            dbc.Col(
                _card(
                    "Running",
                    f"{running}",
                    STATUS_CARD_COLORS["Running"],
                )
            ),
            dbc.Col(
                _card(
                    "Idle",
                    f"{idle}",
                    STATUS_CARD_COLORS["Idle"],
                )
            ),
            dbc.Col(
                _card(
                    "Fault",
                    f"{fault}",
                    STATUS_CARD_COLORS["Fault"],
                )
            ),
            dbc.Col(
                _card(
                    "Under maintenance",
                    f"{maint}",
                    STATUS_CARD_COLORS["UnderMaintenance"],
                )
            ),
            dbc.Col(
                _card(
                    "Average health",
                    f"{avg_health:.1f}",
                    OTHER_CARD_COLORS["Average health"],
                )
            ),
        ],
        className="g-3",
        justify="around",
        style={"margin": "0px", "padding": "0px"},
    )

    return html.Div(cards)


def register_callbacks(app):
    @app.callback(
        Output("store-current", "data"),
        Output("store-workorders", "data"),
        Input("tick", "n_intervals"),
        prevent_initial_call=False,
    )
    def load_data(_n):
        # Load from CSV on each tick for simplicity.
        # If you want live updates later, replace this with DB reads or API calls.
        from .data_loader import load_current_state, load_work_orders

        df_state = load_current_state()
        df_wo = load_work_orders()

        return (
            df_state.to_dict("records"),
            df_wo.to_dict("records"),
        )

    @app.callback(
        Output("filter-plant", "options"),
        Output("filter-line", "options"),
        Output("filter-status", "options"),
        Input("store-current", "data"),
        Input("filter-plant", "value"),
    )
    def set_filter_options(state_json, selected_plants):
        df = pd.DataFrame(state_json) if state_json else pd.DataFrame()

        plant_opts: list[dict] = []
        line_opts: list[dict] = []
        status_opts: list[dict] = []

        if df.empty:
            return plant_opts, line_opts, status_opts

        # Plants
        plant_vals = (
            df[["plantId", "plantName"]]
            .dropna(subset=["plantId", "plantName"])
            .drop_duplicates(subset=["plantId"])
            .sort_values(["plantName"])
        )
        plant_opts = [
            {"label": r["plantName"], "value": int(r["plantId"])}
            for _, r in plant_vals.iterrows()
        ]

        # Decide line option mode based on plant selection
        # - If exactly one plant is selected, show that plant's lines and filter by lineId.
        # - If none or multiple plants are selected, show unique lineName and filter by lineName.
        selected_plants = selected_plants or []
        if isinstance(selected_plants, (int, float)):
            selected_plants = [int(selected_plants)]

        if len(selected_plants) == 1:
            pid = int(selected_plants[0])
            df_lines = df[df["plantId"].astype("Int64") == pid][["lineId", "lineName"]]
            df_lines = (
                df_lines
                .dropna(subset=["lineId", "lineName"])
                .drop_duplicates(subset=["lineId"])
                .assign(
                    _line_num=lambda d: d["lineName"]
                    .astype(str)
                    .str.extract(r"(\d+)", expand=False)
                    .fillna("0")
                    .astype(int)
                )
                .sort_values(["_line_num", "lineName"])
            )
            line_opts = [
                {"label": r["lineName"], "value": int(r["lineId"])}
                for _, r in df_lines.iterrows()
            ]
        else:
            df_lines = df[["lineName"]]
            df_lines = (
                df_lines
                .dropna(subset=["lineName"])
                .drop_duplicates(subset=["lineName"])
                .assign(
                    _line_num=lambda d: d["lineName"]
                    .astype(str)
                    .str.extract(r"(\d+)", expand=False)
                    .fillna("0")
                    .astype(int)
                )
                .sort_values(["_line_num", "lineName"])
            )
            line_opts = [
                {"label": r["lineName"], "value": str(r["lineName"])}
                for _, r in df_lines.iterrows()
            ]

        # Status
        status_vals = sorted(df["resolvedStatus"].dropna().unique().tolist()) if "resolvedStatus" in df.columns else []
        status_opts = [{"label": s, "value": s} for s in status_vals]

        return plant_opts, line_opts, status_opts

    @app.callback(
        Output("kpi-cards", "children"),
        Output("altair-pie", "spec"),
        Output("tab-content", "children"),
        Input("tabs", "value"),
        Input("store-current", "data"),
        Input("store-workorders", "data"),
        Input("filter-plant", "value"),
        Input("filter-line", "value"),
        Input("filter-status", "value"),
        Input("filter-health", "value"),
        Input("filter-stale-only", "value"),
    )
    def render_dashboard(tab, state_json, wo_json, plant, line, statuses, health_rng, stale_flag):
        df = pd.DataFrame(state_json) if state_json else pd.DataFrame()
        df_wo = pd.DataFrame(wo_json) if wo_json else pd.DataFrame()

        stale_only = "stale" in (stale_flag or [])
        filtered = apply_filters(df, plant or [], line or [], statuses, health_rng, stale_only)

        # KPI cards
        cards = make_kpi_cards(filtered)

        # Altair pie, always based on current plant scope
        pie_scope = filtered
        pie_title = "Status distribution (Plant A, Plant B)"
        if plant:
            # Map selected plantIds → plantNames
            plant_names = (
                df[df["plantId"].isin([int(p) for p in plant])]
                [["plantId", "plantName"]]
                .drop_duplicates()
                .sort_values("plantName")["plantName"]
                .tolist()
            )

            if len(plant_names) == 1:
                pie_title = f"Status distribution ({plant_names[0]})"
            else:
                pie_title = "Status distribution (" + ", ".join(plant_names) + ")"
        pie_html = status_pie_chart(pie_scope, title=pie_title)

        if tab == "tab-current":
            # Current view table
            show_cols = [
                "machineId",
                "resolvedStatus",
                "healthScore",
                "openWorkOrderCount",
                "lastUpdateAt",
                "plantName",
                "lineName",
                "machineType",
                "faultCodeId",
                "lastWorkOrderId",
                "lastWorkOrderCreatedByType",
                "lastWorkOrderCreatedById",
            ]
            cols = [c for c in show_cols if c in filtered.columns]
            view = filtered[cols].copy()

            # Add human readable last update
            now = _now_utc()
            if "lastUpdateAt" in view.columns:
                _ts = pd.to_datetime(view["lastUpdateAt"], utc=True, errors="coerce")
                view["lastUpdated"] = _ts.apply(lambda x: ago(x, now))
                # Format the timestamp column for display
                view["lastUpdateAt"] = _ts.dt.strftime("%Y-%m-%d %H:%M")

            from .layout import current_table
            table = current_table()
            table.columns = _datatable_columns(view)
            table.data = view.sort_values("healthScore", ascending=True).to_dict("records")

            return cards, pie_html, html.Div([table])

        # Maintenance queue tab
        # Open work orders table scoped by same filters
        if not df_wo.empty:
            wo = df_wo.copy()

            # Plant scope (multi)
            if plant and "plantId" in wo.columns:
                plant_ids = [int(p) for p in (plant or []) if p is not None]
                if plant_ids:
                    wo = wo[wo["plantId"].astype("Int64").isin(plant_ids)]

            # Line scope (multi)
            # - If line selections are ints, filter by lineId.
            # - If line selections are strings, filter by lineName.
            if line:
                line_ids: list[int] = []
                line_names: list[str] = []
                for v in (line or []):
                    if v is None:
                        continue
                    if isinstance(v, (int, float)) and "lineId" in wo.columns:
                        line_ids.append(int(v))
                    else:
                        line_names.append(str(v))

                if line_ids and "lineId" in wo.columns:
                    wo = wo[wo["lineId"].astype("Int64").isin(line_ids)]
                if line_names and "lineName" in wo.columns:
                    wo = wo[wo["lineName"].astype(str).isin(line_names)]

            now = _now_utc()
            if "createdAt" in wo.columns:
                _created = pd.to_datetime(wo["createdAt"], utc=True, errors="coerce")
                wo["age"] = _created.apply(lambda x: ago(x, now))
                wo["createdAt"] = _created.dt.strftime("%Y-%m-%d %H:%M")

            if "closedAt" in wo.columns:
                _closed = pd.to_datetime(wo["closedAt"], utc=True, errors="coerce")
                wo["closedAt"] = _closed.dt.strftime("%Y-%m-%d %H:%M")
        else:
            wo = pd.DataFrame(columns=["workOrderId", "machineId", "status", "createdAt", "age", "createdByType", "createdById", "issueType"])

        from .layout import queue_tables
        table = queue_tables()

        # Fill work orders table
        table.columns = _datatable_columns(wo)
        table.data = wo.sort_values("createdAt", ascending=False).to_dict("records")

        return cards, pie_html, table
