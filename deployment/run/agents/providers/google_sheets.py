from __future__ import annotations

from typing import Any
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


def _get_sheets(creds_dict: dict[str, Any]):
    credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


async def log_row(sheet_id: str, creds_dict: dict[str, Any], data: dict[str, Any]) -> None:
    service = _get_sheets(creds_dict)
    values = [[str(k), str(v)] for k, v in data.items()]
    body = {"values": values}
    (
        service.spreadsheets()  # type: ignore
        .values()
        .append(spreadsheetId=sheet_id, range="A1", valueInputOption="RAW", body=body)
        .execute()
    )
    return None
