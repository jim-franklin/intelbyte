from __future__ import annotations

import dash
import dash_bootstrap_components as dbc

from src.layout import build_layout
from src.callbacks import register_callbacks

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Factory Equipment Health and Maintenance Dashboard",
)

app.layout = build_layout(app)
register_callbacks(app)

server = app.server

if __name__ == "__main__":
    app.run(debug=True)
