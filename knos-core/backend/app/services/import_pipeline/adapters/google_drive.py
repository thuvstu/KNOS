# backend/app/services/import_pipeline/adapters/google_drive.py
"""Google Drive API v3 adapter"""
import httpx
import structlog
from dataclasses import dataclass
from typing import Optional

logger = structlog.get_logger()
DRIVE_BASE = "https://www.googleapis.com/drive/v3"
DOCS_EXPORT_BASE = "https://www.googleapis.com/drive/v3/files"


@dataclass
class DriveFile:
    file_id: str
    name: str
    mime_type: str
    content: str
    modified_time: str


async def import_drive_file(file_id: str, access_token: str) -> Optional[DriveFile]:
    """Google DriveファイルのテキストをエクスポートしてKnOS entryに変換"""
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        # ファイルメタデータ取得
        meta_resp = await client.get(
            f"{DRIVE_BASE}/files/{file_id}",
            params={"fields": "id,name,mimeType,modifiedTime"},
        )
        meta_resp.raise_for_status()
        meta = meta_resp.json()

        mime = meta.get("mimeType", "")
        name = meta.get("name", "Untitled")

        # Google Docsはtext/plain形式でエクスポート
        if "google-apps" in mime:
            export_mime = "text/plain"
            if "spreadsheet" in mime:
                export_mime = "text/csv"
            elif "presentation" in mime:
                export_mime = "text/plain"

            content_resp = await client.get(
                f"{DOCS_EXPORT_BASE}/{file_id}/export",
                params={"mimeType": export_mime},
            )
            content_resp.raise_for_status()
            content = content_resp.text
        else:
            # バイナリはダウンロードしてテキスト変換（PDFなど）
            content_resp = await client.get(f"{DRIVE_BASE}/files/{file_id}?alt=media")
            content_resp.raise_for_status()
            content = content_resp.text[:50000]  # 50KB上限

    logger.info("drive_file_imported", file_id=file_id, name=name)
    return DriveFile(
        file_id=file_id,
        name=name,
        mime_type=mime,
        content=content,
        modified_time=meta.get("modifiedTime", ""),
    )


async def list_drive_files(access_token: str, query: str = "", max_results: int = 20) -> list[dict]:
    """Driveファイル一覧取得"""
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "pageSize": max_results,
        "fields": "files(id,name,mimeType,modifiedTime)",
    }
    if query:
        params["q"] = query

    async with httpx.AsyncClient(headers=headers, timeout=15) as client:
        resp = await client.get(f"{DRIVE_BASE}/files", params=params)
        resp.raise_for_status()
        return resp.json().get("files", [])
