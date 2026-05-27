# backend/app/routers/srs.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date
from uuid import UUID

from ..database import get_db
from ..models.entry import SrsReview, Entry, EntryType
from ..schemas.entry import SrsReviewCreate, SrsReviewResponse
from ..services.srs import sm2_review, SrsState
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/srs", tags=["srs"])


@router.get("/queue")
async def get_review_queue(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """今日復習すべきエントリー一覧（SM-2の next_review <= today）"""
    today = date.today()

    # 最新レビューを取得するサブクエリ
    latest_subq = (
        select(
            SrsReview.entry_id,
            func.max(SrsReview.reviewed_at).label("latest"),
        )
        .group_by(SrsReview.entry_id)
        .subquery()
    )

    rows = await db.execute(
        select(SrsReview, Entry)
        .join(latest_subq, (SrsReview.entry_id == latest_subq.c.entry_id) &
              (SrsReview.reviewed_at == latest_subq.c.latest))
        .join(Entry, Entry.id == SrsReview.entry_id)
        .where(
            SrsReview.next_review <= today,
            Entry.deleted_at.is_(None),
        )
        .order_by(SrsReview.next_review.asc())
        .limit(limit)
    )

    queue = []
    for review, entry in rows:
        queue.append({
            "entry_id": str(entry.id),
            "title": entry.title,
            "content": entry.content,
            "type": entry.type.value,
            "ease_factor": review.ease_factor,
            "interval": review.interval,
            "next_review": review.next_review.isoformat(),
            "grade_last": review.grade,
        })

    return {"queue": queue, "total": len(queue)}


@router.post("/{entry_id}", response_model=SrsReviewResponse, status_code=201)
async def record_review(
    entry_id: UUID,
    body: SrsReviewCreate,
    db: AsyncSession = Depends(get_db),
):
    """SM-2アルゴリズムでレビューを記録し、次回日程を計算"""
    entry = await db.get(Entry, entry_id)
    if not entry or entry.deleted_at:
        raise HTTPException(status_code=404, detail="Entry not found")

    # 前回状態を取得
    prev = await db.execute(
        select(SrsReview)
        .where(SrsReview.entry_id == entry_id)
        .order_by(SrsReview.reviewed_at.desc())
        .limit(1)
    )
    prev_review = prev.scalar_one_or_none()

    if prev_review:
        state = SrsState(
            ease_factor=prev_review.ease_factor,
            interval=prev_review.interval,
            repetitions=1,  # 既存のレビューがあれば継続
        )
    else:
        state = SrsState()

    new_state, next_date = sm2_review(state, body.grade)

    review = SrsReview(
        entry_id=entry_id,
        grade=body.grade,
        ease_factor=new_state.ease_factor,
        interval=new_state.interval,
        next_review=next_date,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    logger.info(
        "srs_reviewed",
        entry_id=str(entry_id),
        grade=body.grade,
        interval=new_state.interval,
        next_review=str(next_date),
    )
    return review


@router.get("/stats")
async def get_srs_stats(db: AsyncSession = Depends(get_db)):
    """SRS全体統計"""
    today = date.today()
    total_enrolled = (await db.execute(
        select(func.count(func.distinct(SrsReview.entry_id)))
    )).scalar_one()

    due_today = (await db.execute(
        select(func.count(func.distinct(SrsReview.entry_id)))
        .where(SrsReview.next_review <= today)
    )).scalar_one()

    return {
        "total_enrolled": total_enrolled,
        "due_today": due_today,
        "date": today.isoformat(),
    }


@router.post("/{entry_id}/enroll", status_code=201)
async def enroll_entry(entry_id: UUID, db: AsyncSession = Depends(get_db)):
    """エントリーをSRSに登録（初期レビュー作成）"""
    entry = await db.get(Entry, entry_id)
    if not entry or entry.deleted_at:
        raise HTTPException(status_code=404, detail="Entry not found")

    existing = await db.execute(
        select(SrsReview).where(SrsReview.entry_id == entry_id).limit(1)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already enrolled")

    review = SrsReview(
        entry_id=entry_id,
        grade=0,
        ease_factor=2.5,
        interval=1,
        next_review=date.today(),
    )
    db.add(review)
    await db.commit()
    return {"status": "enrolled", "entry_id": str(entry_id)}
