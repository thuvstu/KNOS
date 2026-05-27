# backend/app/services/import_pipeline/file_importer.py
import os
import hashlib
import structlog
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logger = structlog.get_logger()

BLOB_BASE = Path(os.environ.get("KNOS_BLOB_DIR", "/home/knos/blobs"))


@dataclass
class FileImportResult:
    title: str
    content: str
    mime_type: str
    pages: Optional[int] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None


async def import_file(file_bytes: bytes, filename: str) -> Optional[FileImportResult]:
    ext = Path(filename).suffix.lower()
    mime_type = _ext_to_mime(ext)

    # ファイルを保存
    file_path = await _save_blob(file_bytes, filename)
    file_size = len(file_bytes)

    if ext == ".pdf":
        return await _import_pdf(file_bytes, filename, file_path, file_size)
    elif ext == ".docx":
        return await _import_docx(file_bytes, filename, file_path, file_size)
    elif ext == ".txt":
        content = file_bytes.decode("utf-8", errors="replace")
        return FileImportResult(
            title=Path(filename).stem,
            content=content,
            mime_type="text/plain",
            file_path=str(file_path),
            file_size=file_size,
        )
    else:
        logger.warning("unsupported_file_type", ext=ext)
        return None


async def _import_pdf(file_bytes: bytes, filename: str, file_path: Optional[Path], file_size: int) -> Optional[FileImportResult]:
    try:
        import pdfplumber
        import io

        texts = []
        pages = 0
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)

        content = "\n\n".join(texts)
        title = Path(filename).stem

        # 最初のページのテキストからタイトルを推測
        if texts:
            first_lines = texts[0].split("\n")[:3]
            candidate = next((l.strip() for l in first_lines if len(l.strip()) > 5), None)
            if candidate:
                title = candidate[:100]

        logger.info("pdf_imported", filename=filename, pages=pages, chars=len(content))
        return FileImportResult(
            title=title,
            content=content,
            mime_type="application/pdf",
            pages=pages,
            file_path=str(file_path) if file_path else None,
            file_size=file_size,
        )
    except Exception as e:
        logger.error("pdf_import_failed", filename=filename, error=str(e))
        return None


async def _import_docx(file_bytes: bytes, filename: str, file_path: Optional[Path], file_size: int) -> Optional[FileImportResult]:
    try:
        from docx import Document
        import io

        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        content = "\n\n".join(paragraphs)
        title = paragraphs[0][:100] if paragraphs else Path(filename).stem

        logger.info("docx_imported", filename=filename, paragraphs=len(paragraphs))
        return FileImportResult(
            title=title,
            content=content,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_path=str(file_path) if file_path else None,
            file_size=file_size,
        )
    except Exception as e:
        logger.error("docx_import_failed", filename=filename, error=str(e))
        return None


async def _save_blob(file_bytes: bytes, filename: str) -> Optional[Path]:
    try:
        from datetime import datetime
        year = datetime.now().year
        dest_dir = BLOB_BASE / "documents" / str(year)
        dest_dir.mkdir(parents=True, exist_ok=True)

        sha = hashlib.sha256(file_bytes).hexdigest()[:12]
        ext = Path(filename).suffix
        dest = dest_dir / f"{sha}{ext}"
        dest.write_bytes(file_bytes)
        return dest
    except Exception as e:
        logger.warning("blob_save_failed", error=str(e))
        return None


def _ext_to_mime(ext: str) -> str:
    return {
        ".pdf":  "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt":  "text/plain",
        ".md":   "text/markdown",
    }.get(ext, "application/octet-stream")
