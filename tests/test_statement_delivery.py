from datetime import date

from src.statement_models import MonthlyStatementRequest
from src.usage_statement_service import deliver_statement


class RecordingClient:
    def __init__(self) -> None:
        self.email_html: list[str] = []
        self.keys: list[str] = []
        self.pdf_urls = iter(
            [
                "https://downloads.example/statement.pdf",
                "https://downloads.example/statement.pdf",
                "https://downloads.example/regenerated-statement.pdf",
            ]
        )

    def account_usage(self) -> dict[str, object]:
        return {"period": "2026-08", "total": 42}

    def generate_pdf(self, html: str, idempotency_key: str) -> dict[str, object]:
        assert "Northwind CLI" in html
        self.keys.append(idempotency_key)
        return {"url": next(self.pdf_urls)}

    def send_email(
        self, to: str, subject: str, html: str, idempotency_key: str
    ) -> dict[str, object]:
        assert to == "ops@northwind.example"
        assert subject == "Developer usage statement: August 2026"
        self.email_html.append(html)
        self.keys.append(idempotency_key)
        return {"message_id": "msg_123"}


def test_email_idempotency_key_tracks_the_generated_pdf_url() -> None:
    request = MonthlyStatementRequest(
        customer_name="Northwind CLI",
        recipient="ops@northwind.example",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
    )
    client = RecordingClient()

    first = deliver_statement(request, client)  # type: ignore[arg-type]
    replay = deliver_statement(request, client)  # type: ignore[arg-type]
    regenerated = deliver_statement(request, client)  # type: ignore[arg-type]

    assert first.message_id == "msg_123"
    assert first.pdf_url in client.email_html[0]
    assert replay.pdf_url in client.email_html[1]
    assert regenerated.pdf_url in client.email_html[2]
    pdf_keys = client.keys[::2]
    email_keys = client.keys[1::2]
    assert len(set(pdf_keys)) == 1
    assert email_keys[0] == email_keys[1]
    assert email_keys[2] != email_keys[0]
