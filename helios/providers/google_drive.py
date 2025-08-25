from __future__ import annotations

from typing import Any, Iterable, Dict, List
import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
]


def _get_drive(creds_dict: Dict[str, Any]):
    credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


async def upload_assets(
    files: List[str],
    folder_id: str,
    creds_dict: Dict[str, Any],
) -> List[Dict[str, Any]]:
    drive = _get_drive(creds_dict)
    results: List[Dict[str, Any]] = []
    for path in files:
        body = {"name": path.split("/")[-1], "parents": [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(b"placeholder-bytes"), mimetype="application/octet-stream")
        file = (
            drive.files()  # type: ignore
            .create(body=body, media_body=media, fields="id, name, webViewLink")
            .execute()
        )
        results.append({"file": path, "status": "uploaded", **file})
    return results
