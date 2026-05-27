# backend/app/services/search.py
import time
from typing import Optional
from uuid import UUID
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from ..models.entry import Entry, EntryType
from ..schemas.entry import SearchQuery, SearchResponse, SearchResult, EntryResponse
from .embedding import get_embedding_service

logger = structlog.get_logger()

RRF_K = 60  # Reciprocal Rank Fusion constant


async def hybrid_search(
    session: AsyncSession,
    query: SearchQuery,
) -> SearchResponse:
    timings: dict[str, float] = {}
    start_total = time.monotonic()

    q_text = query.q.strip()
    results: list[SearchResult] = []

    if query.mode == "hybrid" and q_text:
        results = await _hybrid(session, query, timings)
    elif query.mode == "semantic" and q_text:
        results = await _semantic(session, query, timings)
    elif query.mode == "fulltext" and q_text:
        results = await _fulltext(session, query, timings)
    else:
        results = await _list_all(session, query, timings)

    timings["total"] = round((time.monotonic() - start_total) * 1000, 2)
    logger.info("search_completed", mode=query.mode, q=q_text, results=len(results), **timings)

    return SearchResponse(results=results, total=len(results), timing_ms=timings)


async def _fulltext(session: AsyncSession, query: SearchQuery, timings: dict) -> list[SearchResult]:
    t0 = time.monotonic()
    sql = _build_base_query(query) + """
        AND (
          title &@~ :q OR content &@~ :q
        )
        ORDER BY pgroonga_score(tableoid, ctid) DESC
        LIMIT :limit OFFSET :offset
    """
    rows = await session.execute(
        text(sql),
        {"q": query.q, "type": query.type, "limit": query.limit, "offset": query.offset},
    )
    timings["fulltext_ms"] = round((time.monotonic() - t0) * 1000, 2)
    return [_row_to_result(r, score=r[1] if len(r) > 1 else 1.0) for r in rows]


async def _semantic(session: AsyncSession, query: SearchQuery, timings: dict) -> list[SearchResult]:
    t0 = time.monotonic()
    svc = get_embedding_service()
    vec = await svc.generate(query.q)
    timings["embed_ms"] = round((time.monotonic() - t0) * 1000, 2)
    if not vec:
        return []

    t1 = time.monotonic()
    vec_str = f"[{','.join(str(v) for v in vec)}]"
    sql = f"""
        SELECT e.*, 1 - (em.vector <=> '{vec_str}'::vector) AS score
        FROM entry e
        JOIN embedding em ON e.id = em.entry_id
        WHERE e.deleted_at IS NULL
          {_type_filter(query)} {_tag_filter(query)}
        ORDER BY em.vector <=> '{vec_str}'::vector
        LIMIT :limit OFFSET :offset
    """
    rows = await session.execute(text(sql), {"limit": query.limit, "offset": query.offset})
    timings["vector_ms"] = round((time.monotonic() - t1) * 1000, 2)
    return [_row_to_result(r, score=float(r[-1])) for r in rows]


async def _hybrid(session: AsyncSession, query: SearchQuery, timings: dict) -> list[SearchResult]:
    """RRF (Reciprocal Rank Fusion) で全文検索 + セマンティック検索を統合"""
    t0 = time.monotonic()

    # 全文検索ランク
    ft_sql = _build_base_query(query) + """
        AND (title &@~ :q OR content &@~ :q)
        ORDER BY pgroonga_score(tableoid, ctid) DESC
        LIMIT 50
    """
    ft_rows = await session.execute(text(ft_sql), {"q": query.q, "type": query.type})
    ft_ids = [str(r[0]) for r in ft_rows]
    timings["fulltext_ms"] = round((time.monotonic() - t0) * 1000, 2)

    # セマンティック検索ランク
    svc = get_embedding_service()
    t1 = time.monotonic()
    vec = await svc.generate(query.q)
    timings["embed_ms"] = round((time.monotonic() - t1) * 1000, 2)

    sem_ids: list[str] = []
    if vec:
        vec_str = f"[{','.join(str(v) for v in vec)}]"
        t2 = time.monotonic()
        sem_sql = f"""
            SELECT e.id
            FROM entry e
            JOIN embedding em ON e.id = em.entry_id
            WHERE e.deleted_at IS NULL
              {_type_filter(query)}
            ORDER BY em.vector <=> '{vec_str}'::vector
            LIMIT 50
        """
        sem_rows = await session.execute(text(sem_sql))
        sem_ids = [str(r[0]) for r in sem_rows]
        timings["vector_ms"] = round((time.monotonic() - t2) * 1000, 2)

    # RRF スコア計算
    rrf: dict[str, float] = {}
    for i, eid in enumerate(ft_ids):
        rrf[eid] = rrf.get(eid, 0) + 1 / (RRF_K + i + 1)
    for i, eid in enumerate(sem_ids):
        rrf[eid] = rrf.get(eid, 0) + 1 / (RRF_K + i + 1)

    if not rrf:
        return []

    # 上位エントリーを取得
    ranked = sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:query.limit]
    ids = [r[0] for r in ranked]
    scores = {r[0]: r[1] for r in ranked}

    id_list = ", ".join(f"'{i}'" for i in ids)
    rows = await session.execute(
        text(f"SELECT * FROM entry WHERE id IN ({id_list}) AND deleted_at IS NULL")
    )
    row_map = {str(r[0]): r for r in rows}

    results = []
    for eid in ids:
        if eid in row_map:
            results.append(_row_to_result(row_map[eid], score=scores[eid]))

    return results


async def _list_all(session: AsyncSession, query: SearchQuery, timings: dict) -> list[SearchResult]:
    t0 = time.monotonic()
    sql = _build_base_query(query) + " ORDER BY e.created_at DESC LIMIT :limit OFFSET :offset"
    rows = await session.execute(text(sql), {"q": "", "type": query.type, "limit": query.limit, "offset": query.offset})
    timings["list_ms"] = round((time.monotonic() - t0) * 1000, 2)
    return [_row_to_result(r, score=1.0) for r in rows]


def _build_base_query(query: SearchQuery) -> str:
    type_clause = f"AND e.type = '{query.type}'" if query.type else ""
    return f"SELECT e.* FROM entry e WHERE e.deleted_at IS NULL {type_clause}"


def _type_filter(query: SearchQuery) -> str:
    return f"AND e.type = '{query.type}'" if query.type else ""


def _tag_filter(query: SearchQuery) -> str:
    if not query.tags:
        return ""
    # 簡易実装: entry_tagテーブルとJOINは省略してサブクエリで
    return ""


def _row_to_result(row: tuple, score: float) -> SearchResult:
    from datetime import datetime
    from uuid import UUID as _UUID

    entry_data = {
        "id": row[0],
        "type": row[1],
        "title": row[2],
        "content": row[3],
        "source_url": row[4] if len(row) > 4 else "",
        "lang": row[5] if len(row) > 5 else "ja",
        "is_favorite": row[6] if len(row) > 6 else False,
        "is_muted": row[7] if len(row) > 7 else False,
        "metadata_": row[8] if len(row) > 8 else {},
        "created_at": row[9] if len(row) > 9 else datetime.utcnow(),
        "updated_at": row[10] if len(row) > 10 else datetime.utcnow(),
        "accessed_at": None,
        "deleted_at": None,
        "tags": [],
        "topics": [],
        "has_embedding": False,
    }
    return SearchResult(
        entry=EntryResponse.model_validate(entry_data),
        score=score,
    )
