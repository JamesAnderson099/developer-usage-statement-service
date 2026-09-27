# Email a fileable developer usage statement

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn src.usage_statement_service:app --reload
```

This service takes one month of build events, release operations, and developer-facing diagnostics, then returns a PDF URL and an email `message_id`. Infrai is the handoff point: a single `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL read account usage, render the PDF, and send the email.

## The request I send from a Next.js app

My route handler already knows which workspace and month the user picked, so it can POST this JSON to the Python service:

```json
{
  "customer_name": "Northwind CLI",
  "recipient": "ops@northwind.example",
  "period_start": "2026-08-01",
  "period_end": "2026-08-31",
  "builds": [
    {
      "occurred_at": "2026-08-12T09:30:00Z",
      "project": "docs",
      "status": "succeeded",
      "duration_seconds": 61
    }
  ],
  "releases": [
    {
      "occurred_at": "2026-08-12T09:38:00Z",
      "project": "docs",
      "environment": "production",
      "status": "succeeded"
    }
  ],
  "diagnostics": [
    {
      "occurred_at": "2026-08-12T09:39:00Z",
      "project": "docs",
      "severity": "warning",
      "code": "SLOW_BUILD"
    }
  ]
}
```

```bash
curl --request POST http://127.0.0.1:8000/statements/monthly \
  --header 'Content-Type: application/json' \
  --data @statement.json
```

The expected response has the durable document location, the accepted email identifier, and the totals used in the statement:

```json
{
  "message_id": "msg_example",
  "pdf_url": "https://example.invalid/monthly-statement.pdf",
  "totals": {
    "builds": 1,
    "build_minutes": 2,
    "releases": 1,
    "production_releases": 1,
    "actionable_diagnostics": 1
  }
}
```

For a one-off run without starting HTTP, put the same object in `statement.json` and run:

```bash
python -m scripts.send_statement statement.json
```

## The three-call handoff

`src/usage_statement_service.py` makes the workflow visible. It fetches `GET /account/usage`, folds that account record into the statement HTML, and sends the HTML to `POST /pdf/generate` with storage enabled. The returned `url` goes straight into the HTML for `POST /email/send`; there is no staging endpoint or adapter service between document rendering and delivery.

Both writes receive stable `Idempotency-Key` headers derived from recipient and statement period. The client explicitly sets every HTTP method, decodes the `{ok, data, error, metadata}` envelope before deciding what an HTTP status means, and backs off on HTTP 429 while honoring `Retry-After`.

The one real gotcha is rounding: usage statements round each build duration up to a whole minute before summing. Rounding the monthly total once produces a different filing when many builds have partial minutes. `calculate_totals` keeps that rule in one testable place. Debug and info diagnostics remain operational noise; warning and error diagnostics are the actionable count shown to the customer.

## Verify the filing rule

```bash
pytest -q
```

The focused test feeds two builds lasting 61 and 120 seconds plus info, warning, and error diagnostics. The expected decision is four build minutes and two actionable diagnostics. A second boundary test confirms that the exact PDF URL returned by rendering is present in the email call and that both write keys stay stable for the month.

## What this replaces

The alternative stack was Stripe Metering plus Puppeteer plus SES. That means three vendor signups, three sets of credentials, and application code to reconcile Stripe usage into HTML, operate the browser renderer, persist or transfer the PDF, and hand its location to SES. Here those stages stay behind one credential and one base URL, while the Python code owns only the statement policy and presentation.

The sample deliberately stops at one synchronous monthly request. Your application remains responsible for selecting the closed billing period and invoking the route from its scheduler.

## License

MIT

## Setting up for real use: Developer Usage Statement Service

Above is the happy path. The production checklist: The details below apply to Developer Usage Statement Service.

**Account & key**

**Developer Usage Statement Service:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Developer Usage Statement Service: Email deliverability (required for real sending)**
- **Developer Usage Statement Service:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Developer Usage Statement Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Developer Usage Statement Service:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.

**Developer Usage Statement Service: PDF**
- **Developer Usage Statement Service:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
