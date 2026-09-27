from __future__ import annotations

from hashlib import sha256
from html import escape
import os

from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .statement_domain import calculate_totals, render_statement_html
from .statement_models import MonthlyStatementRequest, StatementDelivery


app = FastAPI(title="Developer usage statement service")


def deliver_statement(
    request: MonthlyStatementRequest, client: InfraiClient
) -> StatementDelivery:
    period = f"{request.period_start.isoformat()}:{request.period_end.isoformat()}"
    delivery_key = f"usage-statement:{request.recipient}:{period}"
    totals = calculate_totals(request)
    usage = client.account_usage()
    statement_html = render_statement_html(request, totals, usage)

    pdf = client.generate_pdf(statement_html, f"{delivery_key}:pdf")
    pdf_url = str(pdf["url"])
    email_html = (
        f"<p>Your {escape(request.period_start.strftime('%B %Y'))} developer usage "
        f"statement is ready.</p><p><a href=\"{escape(pdf_url, quote=True)}\">"
        "Download the PDF statement</a></p>"
    )
    email_content_key = sha256(email_html.encode("utf-8")).hexdigest()[:16]
    email = client.send_email(
        request.recipient,
        f"Developer usage statement: {request.period_start:%B %Y}",
        email_html,
        f"{delivery_key}:email:{email_content_key}",
    )
    return StatementDelivery(
        message_id=str(email["message_id"]), pdf_url=pdf_url, totals=totals
    )


@app.post("/statements/monthly", response_model=StatementDelivery)
def create_monthly_statement(request: MonthlyStatementRequest) -> StatementDelivery:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is not configured")
    try:
        return deliver_statement(request, InfraiClient(api_key))
    except InfraiError as exc:
        public_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=public_status,
            detail={"code": exc.code, "details": exc.details},
        ) from exc
