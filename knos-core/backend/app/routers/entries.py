# backend/app/routers/entries.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from uuid import UUID
from datetime import datetime
from typing import Optional

from ..database import get_db
from ..models.entry import Entry, EntryType, Tag, EntryTag
from ..schemas.entry import EntryCreate, EntryUpdate, EntryResponse, EntryListResponse
from ..services.embedding import get_embedding_service
from ..services.connection import generate_connection_candidates
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/entries", tags=["entries"])


@router.get("", response_model=EntryListResponse)
async def list_entries(
    type: Optional[EntryType] = None,
    tag: Optional[str] = None,
    favorite: Optional[bool] = None,
    offset: int = 0,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(Entry).where(Entry.deleted_at.is_(None))
    if type:
        q = q.where(Entry.type == type)
    if favorite is not None:
        q = q.where(Entry.is_favorite == favorite)
    if tag:
        q = q.join(EntryTag).join(Tag).where(Tag.name == tag)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    q = q.order_by(Entry.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    return EntryListResponse(
        items=[_to_response(e) for e in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=EntryResponse, status_code=201)
async def create_entry(
    body: EntryCreate,
    db: AsyncSession = Depends(get_db),
):
    entry = Entry(
        type=body.type,
        title=body.title,
        content=body.content,
        source_url=body.source_url,
        lang=body.lang,
        metadata_=body.metadata,
    )
    db.add(entry)
    await db.flush()  # IDを発行

    # タグ処理
    for tag_name in body.tags:
        tag = await _get_or_create_tag(db, tag_name)
        db.add(EntryTag(entry_id=entry.id, tag_id=tag.id))

    # 型別拡張テーブル
    if body.ext:
        await _create_extension(db, entry, body.ext)

    await db.commit()
    await db.refresh(entry)

    # Embedding キューに追加
    input_text = f"{entry.title}\n{entry.content}".strip()
    if input_text:
        get_embedding_service().enqueue(entry.id, input_text)

    logger.info("entry_created", entry_id=str(entry.id), type=entry.type, title=entry.title[:50])
    return _to_response(entry)


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(entry_id: UUID, db: AsyncSession = Depends(get_db)):
    entry = await db.get(Entry, entry_id)
    if not entry or entry.deleted_at:
        raise HTTPException(status_code=404, detail="Entry not found")

    # accessed_at 更新
    entry.accessed_at = datetime.utcnow()
    await db.commit()

    return _to_response(entry)


@router.patch("/{entry_id}", response_model=EntryResponse)
async def update_entry(entry_id: UUID, body: EntryUpdate, db: AsyncSession = Depends(get_db)):
    entry = await db.get(Entry, entry_id)
    if not entry or entry.deleted_at:
        raise HTTPException(status_code=404, detail="Entry not found")

    if body.title is not None:   entry.title = body.title
    if body.content is not None: entry.content = body.content
    if body.source_url is not None: entry.source_url = body.source_url
    if body.lang is not None:    entry.lang = body.lang
    if body.is_favorite is not None: entry.is_favorite = body.is_favorite
    if body.is_muted is not None:    entry.is_muted = body.is_muted
    if body.metadata is not None:    entry.metadata_ = body.metadata

    if body.tags is not None:
        await db.execute(
            text("DELETE FROM entry_tag WHERE entry_id = :id"),
            {"id": str(entry_id)},
        )
        for tag_name in body.tags:
            tag = await _get_or_create_tag(db, tag_name)
            db.add(EntryTag(entry_id=entry.id, tag_id=tag.id))

    await db.commit()
    await db.refresh(entry)

    # Embeddingを再キュー
    input_text = f"{entry.title}\n{entry.content}".strip()
    if input_text:
        get_embedding_service().enqueue(entry.id, input_text)

    return _to_response(entry)


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(entry_id: UUID, db: AsyncSession = Depends(get_db)):
    entry = await db.get(Entry, entry_id)
    if not entry or entry.deleted_at:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry.deleted_at = datetime.utcnow()
    await db.commit()
    logger.info("entry_deleted", entry_id=str(entry_id))


@router.post("/{entry_id}/restore", response_model=EntryResponse)
async def restore_entry(entry_id: UUID, db: AsyncSession = Depends(get_db)):
    entry = await db.get(Entry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not entry.deleted_at:
        raise HTTPException(status_code=400, detail="Entry is not deleted")

    entry.deleted_at = None
    await db.commit()
    await db.refresh(entry)
    return _to_response(entry)


# ─── helpers ───

def _to_response(entry: Entry) -> EntryResponse:
    return EntryResponse(
        id=entry.id,
        type=entry.type,
        title=entry.title,
        content=entry.content,
        source_url=entry.source_url,
        lang=entry.lang,
        is_favorite=entry.is_favorite,
        is_muted=entry.is_muted,
        metadata_=entry.metadata_ or {},
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        accessed_at=entry.accessed_at,
        deleted_at=entry.deleted_at,
        tags=[{"id": t.id, "name": t.name} for t in (entry.tags or [])],
        topics=[{"id": t.id, "name": t.name} for t in (entry.topics or [])],
        has_embedding=entry.embedding is not None,
    )


async def _get_or_create_tag(db: AsyncSession, name: str) -> Tag:
    result = await db.execute(select(Tag).where(Tag.name == name))
    tag = result.scalar_one_or_none()
    if not tag:
        tag = Tag(name=name)
        db.add(tag)
        await db.flush()
    return tag


async def _create_extension(db: AsyncSession, entry: Entry, ext: dict):
    from ..models.entry import (
        EntryWebpage, EntryThought, EntryBook, EntryVideo, EntryDocument,
        EntryPerson, EntryOrg, EntryPlace, EntryEvent, EntryDefinition,
        EntryLiked, EntryAiConv,
    )

    ext_map = {
        "webpage":    EntryWebpage,
        "thought":    EntryThought,
        "book":       EntryBook,
        "video":      EntryVideo,
        "document":   EntryDocument,
        "person":     EntryPerson,
        "org":        EntryOrg,
        "place":      EntryPlace,
        "event":      EntryEvent,
        "definition": EntryDefinition,
        "liked":      EntryLiked,
        "ai_conv":    EntryAiConv,
    }

    cls = ext_map.get(entry.type.value)
    if cls:
        obj = cls(entry_id=entry.id, **{k: v for k, v in ext.items() if hasattr(cls, k)})
        db.add(obj)
