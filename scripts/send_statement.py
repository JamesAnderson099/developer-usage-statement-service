from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from src.infrai_client import InfraiClient
from src.statement_models import MonthlyStatementRequest
from src.usage_statement_service import deliver_statement


def main() -> None:
    parser = argparse.ArgumentParser(description="Send one monthly usage statement")
    parser.add_argument("request", type=Path, help="Path to a statement request JSON file")
    args = parser.parse_args()
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("Set INFRAI_API_KEY before sending a statement")

    statement = MonthlyStatementRequest.model_validate_json(
        args.request.read_text(encoding="utf-8")
    )
    result = deliver_statement(statement, InfraiClient(api_key))
    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
