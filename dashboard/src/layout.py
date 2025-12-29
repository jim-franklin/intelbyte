from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table
import dash_vega_components as dvc


def build_layout(app: dash.Dash) -> html.Div:
    return dbc.Container(
        fluid=True,
        children=[
            dcc.Store(id="store-current"),
            dcc.Store(id="store-workorders"),
            dcc.Interval(id="tick", interval=60_000, n_intervals=0),

            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H4("Filters", className="mt-2"),
                            html.Br(),
                            dbc.Label("Plant"),
                            dcc.Dropdown(
                                id="filter-plant",
                                multi=True,
                                placeholder="All plants"
                            ),
                            html.Br(),
                            dbc.Label("Production line", className="mt-2"),
                            dcc.Dropdown(
                                id="filter-line",
                                multi=True,
                                placeholder="All lines"
                            ),
                            html.Br(),
                            dbc.Label("Resolved status", className="mt-2"),
                            dcc.Dropdown(
                                id="filter-status",
                                multi=True,
                                placeholder="All statuses",
                            ),
                            html.Br(),
                            dbc.Label("Health score range", className="mt-2"),
                            dcc.RangeSlider(
                                id="filter-health",
                                min=0,
                                max=100,
                                step=1,
                                value=[0, 100],
                                marks={0: "0", 50: "50", 100: "100"},
                                tooltip={"placement": "bottom", "always_visible": False},
                            ),
                            html.Br(),
                            dbc.Checklist(
                                id="filter-stale-only",
                                options=[{"label": "Show only stale machines (last update older than 30 mins)", "value": "stale"}],
                                value=[],
                                className="mt-3",
                            ),
                            html.Br(),
                            html.Hr(),
                            dcc.Loading(
                                children=dvc.Vega(
                                    id="altair-pie",
                                    spec={},
                                    opt={"actions": False, "renderer": "svg"},
                                    style={
                                        "width": "90%",
                                        "height": "35vh",
                                        "minHeight": "220px",
                                        "margin": "0 auto",
                                    }
                                )
                            ),
                        ],
                        width=3,
                        className="bg-light border-end vh-100",
                        style={"padding": "16px"},
                    ),

                    dbc.Col(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(html.Div(id="kpi-cards"), width=12),
                                ],
                                className="mt-2",
                            ),

                            dcc.Tabs(
                                id="tabs",
                                value="tab-current",
                                children=[
                                    dcc.Tab(label="Current equipment status", value="tab-current"),
                                    dcc.Tab(label="Maintenance Queue", value="tab-queue"),
                                ],
                                className="mt-3",
                            ),

                            html.Div(id="tab-content", className="mt-3"),
                        ],
                        width=9,
                        style={"padding": "16px"},
                    ),
                ]
            ),
        ],
    )


def current_table() -> dash_table.DataTable:
    return dash_table.DataTable(
        id="table-current",
        page_size=20,
        sort_action="native",
        filter_action="native",
        row_selectable=False,
        style_table={'overflowY': 'auto'},
        style_cell={"padding": "6px", "fontFamily": "inherit", "fontSize": 14, "whiteSpace": "nowrap"},
        style_header={"fontWeight": "600"},
        filter_options={"placeholder_text": "Filter.."},
    )


def queue_tables() -> html.Div:
    return dash_table.DataTable(
        id="table-workorders",
        page_size=20,
        sort_action="native",
        filter_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"padding": "6px", "fontFamily": "inherit", "fontSize": 14, "whiteSpace": "nowrap"},
        style_header={"fontWeight": "600"},
        filter_options={"placeholder_text": "Filter.."},
    )
