from __future__ import annotations

import altair as alt
import pandas as pd

alt.data_transformers.enable('default')


def status_pie_chart(df: pd.DataFrame, title: str = "Status distribution") -> str:
    """Return an Altair chart rendered as an HTML string for Dash Iframe srcDoc."""
    if df.empty:
        empty = (
            alt.Chart(pd.DataFrame({"x": [1], "y": [1]}),)
            .mark_text(text="No data", size=18)
            .encode()
            .properties(title=title, width=360, height=260)
        )
        return empty.to_dict(format="vega")

    agg = (
        df.groupby("resolvedStatus", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    chart = (
        alt.Chart(agg, title=title)
        .mark_arc()
        .encode(
            theta=alt.Theta("count:Q"),
            color=alt.Color(
                "resolvedStatus:N",
                legend=alt.Legend(
                    title="",
                    orient="bottom",
                    direction="horizontal",
                ),
            ),
            tooltip=[
                alt.Tooltip("resolvedStatus:N", title="Status"),
                alt.Tooltip("count:Q", title="Machines"),
            ],
        )
        .properties(width=360, height=260)
    )

    # Dash components must receive JSON-serializable values.
    # For an Iframe `srcDoc`, return an HTML string.
    return chart.to_dict(format="vega")
