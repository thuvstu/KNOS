# backend/app/routers/taxonomy.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from ..database import get_db
from ..models.entry import Tag, Topic, EntryTag, EntryTopic, Entry
import structlog

logger = structlog.get_logger()
router = APIRouter(tags=["taxonomy"])


# ─── Tags ───

tags_router = APIRouter(prefix="/tags")


@tags_router.get("")
async def list_tags(q: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Tag, func.count(EntryTag.entry_id).label("count")).outerjoin(
        EntryTag, EntryTag.tag_id == Tag.id
    ).group_by(Tag.id)
    if q:
        stmt = stmt.where(Tag.name.ilike(f"%{q}%"))
    stmt = stmt.order_by(func.count(EntryTag.entry_id).desc()).limit(100)

    rows = (await db.execute(stmt)).all()
    return [{"id": r.Tag.id, "name": r.Tag.name, "count": r.count} for r in rows]


@tags_router.post("", status_code=201)
async def create_tag(name: str, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(Tag).where(Tag.name == name))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Tag already exists")
    tag = Tag(name=name)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return {"id": tag.id, "name": tag.name}


@tags_router.delete("/{tag_id}", status_code=204)
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404)
    await db.delete(tag)
    await db.commit()


# ─── Topics ───

topics_router = APIRouter(prefix="/topics")


@topics_router.get("")
async def list_topics(parent_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Topic)
    if parent_id is not None:
        stmt = stmt.where(Topic.parent_id == parent_id)
    else:
        stmt = stmt.where(Topic.parent_id.is_(None))
    stmt = stmt.order_by(Topic.name)

    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "parent_id": t.parent_id,
            "description": t.description,
        }
        for t in rows
    ]


@topics_router.post("", status_code=201)
async def create_topic(
    name: str,
    description: str = "",
    parent_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    topic = Topic(name=name, description=description, parent_id=parent_id)
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return {"id": topic.id, "name": topic.name, "parent_id": topic.parent_id}


@topics_router.patch("/{topic_id}")
async def update_topic(
    topic_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    parent_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404)
    if name is not None:        topic.name = name
    if description is not None: topic.description = description
    if parent_id is not None:   topic.parent_id = parent_id
    await db.commit()
    return {"id": topic.id, "name": topic.name}


@topics_router.delete("/{topic_id}", status_code=204)
async def delete_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404)
    await db.delete(topic)
    await db.commit()


@topics_router.post("/{topic_id}/entries/{entry_id}", status_code=201)
async def assign_topic_to_entry(
    topic_id: int,
    entry_id: str,
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID
    db.add(EntryTopic(entry_id=UUID(entry_id), topic_id=topic_id))
    await db.commit()
    return {"status": "assigned"}


router.include_router(tags_router)
router.include_router(topics_router)
