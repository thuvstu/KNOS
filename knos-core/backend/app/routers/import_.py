# backend/app/routers/import_.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models.entry import Entry, EntryType
from ..models.entry import EntryWebpage, EntryVideo, EntryDocument, EntryLiked
from ..schemas.entry import ImportUrlRequest, ImportFileResponse, EntryResponse
from ..services.import_pipeline.url_scraper import scrape_url
from ..services.import_pipeline.file_importer import import_file
from ..services.embedding import get_embedding_service
from ..routers.entries import _to_response
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/import", tags=["import"])


@router.post("/url", response_model=EntryResponse)
async def import_url(body: ImportUrlRequest, db: AsyncSession = Depends(get_db)):
    result = await scrape_url(body.url)
    if not result:
        raise HTTPException(status_code=422, detail="スクレイプに失敗しました")

    entry = Entry(
        type=EntryType.webpage,
        title=result.title,
        content=result.content,
        source_url=result.url,
    )
    db.add(entry)
    await db.flush()

    db.add(EntryWebpage(
        entry_id=entry.id,
        url=result.url,
        domain=result.domain,
        author=result.author,
    ))

    # タグ
    from ..routers.entries import _get_or_create_tag
    from ..models.entry import EntryTag
    for tag_name in body.tags:
        tag = await _get_or_create_tag(db, tag_name)
        db.add(EntryTag(entry_id=entry.id, tag_id=tag.id))

    await db.commit()
    await db.refresh(entry)

    input_text = f"{entry.title}\n{entry.content}".strip()
    if input_text:
        get_embedding_service().enqueue(entry.id, input_text)

    logger.info("import_completed", source="url", url=body.url, entry_id=str(entry.id))
    return _to_response(entry)


@router.post("/file", response_model=ImportFileResponse)
async def import_file_endpoint(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    result = await import_file(file_bytes, file.filename or "unknown")
    if not result:
        raise HTTPException(status_code=422, detail="ファイルのインポートに失敗しました")

    entry = Entry(
        type=EntryType.document,
        title=result.title,
        content=result.content,
    )
    db.add(entry)
    await db.flush()

    db.add(EntryDocument(
        entry_id=entry.id,
        file_path=result.file_path,
        mime_type=result.mime_type,
        pages=result.pages,
        file_size=result.file_size,
    ))

    await db.commit()

    input_text = f"{entry.title}\n{entry.content[:2000]}".strip()
    if input_text:
        get_embedding_service().enqueue(entry.id, input_text)

    logger.info("import_completed", source="file", filename=file.filename, entry_id=str(entry.id))
    return ImportFileResponse(entry_id=entry.id, title=result.title, pages=result.pages)


@router.post("/obsidian")
async def import_obsidian(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    from ..services.import_pipeline.adapters.obsidian import import_obsidian_zip
    from ..routers.entries import _get_or_create_tag
    from ..models.entry import EntryTag

    zip_bytes = await file.read()
    notes = import_obsidian_zip(zip_bytes)

    created = []
    for note in notes:
        entry = Entry(type=EntryType.document, title=note.title, content=note.content)
        db.add(entry)
        await db.flush()

        for tag_name in note.tags:
            tag = await _get_or_create_tag(db, tag_name)
            db.add(EntryTag(entry_id=entry.id, tag_id=tag.id))

        created.append(str(entry.id))

    await db.commit()
    logger.info("import_completed", source="obsidian", entries_created=len(created))
    return {"created": len(created), "ids": created}


@router.post("/x-archive")
async def import_x_archive(
    data: list[dict] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    from ..services.import_pipeline.adapters.obsidian import import_x_archive

    tweets = import_x_archive(data, mode="liked")
    created = []

    for tweet in tweets:
        entry = Entry(
            type=EntryType.liked,
            title=tweet.content[:100],
            content=tweet.content,
        )
        db.add(entry)
        await db.flush()

        db.add(EntryLiked(
            entry_id=entry.id,
            platform="twitter",
            original_id=tweet.tweet_id,
            author=tweet.author,
            body_text=tweet.content,
        ))
        created.append(str(entry.id))

    await db.commit()
    logger.info("import_completed", source="x_archive", entries_created=len(created))
    return {"created": len(created)}


@router.post("/youtube")
async def import_youtube(
    playlist_id: str = Body(default=""),
    db: AsyncSession = Depends(get_db),
):
    from ..config import get_settings
    from ..services.import_pipeline.adapters.youtube import import_liked_videos, import_playlist

    settings = get_settings()
    if not settings.youtube_api_key:
        raise HTTPException(status_code=503, detail="YOUTUBE_API_KEY is not configured")

    if playlist_id:
        videos = await import_playlist(playlist_id, settings.youtube_api_key)
    else:
        videos = await import_liked_videos(settings.youtube_api_key)

    created = []
    for v in videos:
        entry = Entry(
            type=EntryType.video,
            title=v.title,
            content=v.description,
            source_url=v.url,
        )
        db.add(entry)
        await db.flush()

        db.add(EntryVideo(
            entry_id=entry.id,
            url=v.url,
            platform="youtube",
            channel=v.channel,
        ))
        created.append(str(entry.id))

    await db.commit()
    logger.info("import_completed", source="youtube", entries_created=len(created))
    return {"created": len(created)}
