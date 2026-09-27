from datetime import date, datetime, timezone

from src.statement_domain import calculate_totals
from src.statement_models import MonthlyStatementRequest


def test_statement_counts_only_actionable_diagnostics_and_rounds_each_build() -> None:
    at = datetime(2026, 8, 12, 9, 30, tzinfo=timezone.utc)
    request = MonthlyStatementRequest.model_validate(
        {
            "customer_name": "Northwind CLI",
            "recipient": "ops@northwind.example",
            "period_start": date(2026, 8, 1),
            "period_end": date(2026, 8, 31),
            "builds": [
                {"occurred_at": at, "project": "docs", "status": "succeeded", "duration_seconds": 61},
                {"occurred_at": at, "project": "api", "status": "failed", "duration_seconds": 120},
            ],
            "releases": [
                {"occurred_at": at, "project": "docs", "environment": "preview", "status": "succeeded"},
                {"occurred_at": at, "project": "api", "environment": "production", "status": "rolled_back"},
            ],
            "diagnostics": [
                {"occurred_at": at, "project": "docs", "severity": "info", "code": "CACHE_HIT"},
                {"occurred_at": at, "project": "api", "severity": "warning", "code": "SLOW_BUILD"},
                {"occurred_at": at, "project": "api", "severity": "error", "code": "DEPLOY_FAILED"},
            ],
        }
    )

    assert calculate_totals(request).model_dump() == {
        "builds": 2,
        "build_minutes": 4,
        "releases": 2,
        "production_releases": 1,
        "actionable_diagnostics": 2,
    }
