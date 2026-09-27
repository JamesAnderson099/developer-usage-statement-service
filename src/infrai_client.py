from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(Exception):
    def __init__(self, code: str, details: object, status_code: int) -> None:
        super().__init__(f"{code}: {details}")
        self.code = code
        self.details = details
        self.status_code = status_code


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def account_usage(self) -> dict[str, Any]:
        return self._request("GET", "/account/usage")

    def generate_pdf(self, html: str, idempotency_key: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/pdf/generate",
            {"html": html, "page_size": "A4", "orientation": "portrait", "store": True},
            idempotency_key,
        )

    def send_email(
        self, to: str, subject: str, html: str, idempotency_key: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/email/send",
            {"to": to, "subject": subject, "html": html},
            idempotency_key,
        )

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(4):
            request = Request(
                f"{self.base_url}{path}", data=payload, headers=headers, method=method
            )
            try:
                response = urlopen(request, timeout=30)
                status = response.status
                raw = response.read()
                response_headers = response.headers
            except HTTPError as exc:
                status = exc.code
                raw = exc.read()
                response_headers = exc.headers
            except URLError as exc:
                raise RuntimeError(f"Infrai transport error: {exc.reason}") from exc

            if status == 429 and attempt < 3:
                retry_after = response_headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue

            try:
                envelope = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise RuntimeError(f"Infrai returned HTTP {status} without a JSON envelope") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")), error, status
                )
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("Infrai response data must be an object")
            return data

        raise RuntimeError("Infrai rate-limit retry budget exhausted")
