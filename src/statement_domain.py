from __future__ import annotations

from html import escape
import json
import math
from typing import Any

from .statement_models import MonthlyStatementRequest, StatementTotals


def calculate_totals(statement: MonthlyStatementRequest) -> StatementTotals:
    """Count customer-facing activity; debug and info diagnostics stay out of filings."""
    return StatementTotals(
        builds=len(statement.builds),
        build_minutes=sum(math.ceil(item.duration_seconds / 60) for item in statement.builds),
        releases=len(statement.releases),
        production_releases=sum(
            item.environment == "production" for item in statement.releases
        ),
        actionable_diagnostics=sum(
            item.severity in {"warning", "error"} for item in statement.diagnostics
        ),
    )


def render_statement_html(
    statement: MonthlyStatementRequest,
    totals: StatementTotals,
    account_usage: dict[str, Any],
) -> str:
    account_snapshot = escape(json.dumps(account_usage, sort_keys=True, default=str))
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Monthly developer usage statement</title></head>
<body style="font-family:Arial,sans-serif;color:#17202a;max-width:760px;margin:40px auto">
  <p style="color:#52606d">Developer tools usage statement</p>
  <h1>{escape(statement.customer_name)}</h1>
  <p>{statement.period_start.isoformat()} through {statement.period_end.isoformat()}</p>
  <table style="border-collapse:collapse;width:100%">
    <tr><th align="left">Activity</th><th align="right">Recorded usage</th></tr>
    <tr><td>Build events</td><td align="right">{totals.builds}</td></tr>
    <tr><td>Build minutes (rounded per build)</td><td align="right">{totals.build_minutes}</td></tr>
    <tr><td>Release operations</td><td align="right">{totals.releases}</td></tr>
    <tr><td>Production releases</td><td align="right">{totals.production_releases}</td></tr>
    <tr><td>Actionable diagnostics</td><td align="right">{totals.actionable_diagnostics}</td></tr>
  </table>
  <h2>Account usage record</h2>
  <pre style="white-space:pre-wrap">{account_snapshot}</pre>
</body>
</html>"""
