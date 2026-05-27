# backend/app/services/connection.py
import structlog
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from ..models.entry import ConnectionCandidate, Connection, ConnectionType
from ..config import get_settings

logger = structlog.get_logger()
settings = get_settings()


async def generate_connection_candidates(session: AsyncSession, entry_id: UUID) -> int:
    """新規エントリーに対する接続候補を生成（類似度 > 閾値）"""
    threshold = settings.auto_connect_threshold

    # 既存のEmbeddingと比較
    sql = text("""
        SELECT e.id, 1 - (em.vector <=> target.vector) AS similarity
        FROM embedding em
        JOIN entry e ON e.id = em.entry_id
        JOIN embedding target ON target.entry_id = :entry_id
        WHERE em.entry_id != :entry_id
          AND e.deleted_at IS NULL
          AND 1 - (em.vector <=> target.vector) > :threshold
        ORDER BY similarity DESC
        LIMIT 20
    """)

    rows = await session.execute(sql, {"entry_id": entry_id, "threshold": threshold})

    count = 0
    for row in rows:
        candidate_id = row[0]
        score = float(row[1])

        # 既存の候補・接続がなければ追加
        existing = await session.execute(
            text("""
                SELECT id FROM connection_candidate
                WHERE (entry_a = :a AND entry_b = :b)
                   OR (entry_a = :b AND entry_b = :a)
            """),
            {"a": str(entry_id), "b": str(candidate_id)},
        )
        if existing.first():
            continue

        # 正式な接続も確認
        conn_exists = await session.execute(
            text("""
                SELECT id FROM connection
                WHERE (entry_a = :a AND entry_b = :b)
                   OR (entry_a = :b AND entry_b = :a)
            """),
            {"a": str(entry_id), "b": str(candidate_id)},
        )
        if conn_exists.first():
            continue

        session.add(ConnectionCandidate(
            entry_a=entry_id,
            entry_b=UUID(str(candidate_id)),
            score=score,
            status="pending",
        ))
        count += 1

    if count > 0:
        await session.commit()
        logger.info("connection_candidates_generated", entry_id=str(entry_id), count=count)

    return count


async def auto_connect_if_enabled(session: AsyncSession, entry_id: UUID):
    """AUTO_CONNECT_ENABLED=true の場合、閾値超えを直接接続に変換"""
    if not settings.auto_connect_enabled:
        return

    threshold = settings.auto_connect_threshold

    sql = text("""
        SELECT e.id, 1 - (em.vector <=> target.vector) AS similarity
        FROM embedding em
        JOIN entry e ON e.id = em.entry_id
        JOIN embedding target ON target.entry_id = :entry_id
        WHERE em.entry_id != :entry_id
          AND e.deleted_at IS NULL
          AND 1 - (em.vector <=> target.vector) > :threshold
        ORDER BY similarity DESC
        LIMIT 10
    """)

    rows = await session.execute(sql, {"entry_id": entry_id, "threshold": threshold})

    for row in rows:
        b_id = UUID(str(row[0]))
        strength = float(row[1])

        conn = Connection(
            entry_a=entry_id,
            entry_b=b_id,
            type=ConnectionType.related,
            strength=strength,
            is_auto=True,
        )
        session.add(conn)
        logger.info("connection_auto_created", entry_a=str(entry_id), entry_b=str(b_id), strength=strength)

    await session.commit()
