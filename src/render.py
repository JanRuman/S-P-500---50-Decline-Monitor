"""Render the HTML report from a Jinja2 template."""

from datetime import datetime, timezone

import pandas as pd
from jinja2 import Environment, FileSystemLoader

import config


def render_report(df: pd.DataFrame) -> str:
    """Render and return the HTML report string."""
    env = Environment(loader=FileSystemLoader("."), autoescape=True)
    template = env.get_template(config.TEMPLATE_PATH)

    rows     = df.to_dict(orient="records") if not df.empty else []
    sectors  = sorted(df["sector"].unique().tolist())   if not df.empty else []
    exchanges = sorted(df["exchange"].unique().tolist()) if not df.empty else []
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return template.render(
        rows=rows,
        sectors=sectors,
        exchanges=exchanges,
        threshold=config.DECLINE_THRESHOLD_PCT,
        min_market_cap_b=config.MIN_MARKET_CAP_B,
        generated_at=generated_at,
        count=len(rows),
    )
