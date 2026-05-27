# backend/app/routers/graph.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from uuid import UUID

from ..database import get_db
from ..models.entry import Connection, ConnectionCandidate, Entry
from ..schemas.entry import ConnectionCreate, ConnectionUpdate, ConnectionResponse, CandidateAction
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/connections/{entry_id}")
async def get_connections(
    entry_id: UUID,
    depth: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """エントリーの接続グラフを返す（depth: 1-4）"""
    depth = min(max(depth, 1), 4)

    visited = set()
    nodes = []
    edges = []

    async def traverse(eid: UUID, current_depth: int):
        if eid in visited or current_depth > depth:
            return
        visited.add(eid)

        entry = await db.get(Entry, eid)
        if entry and not entry.deleted_at:
            nodes.append({"id": str(eid), "title": entry.title, "type": entry.type.value})

        if current_depth >= depth:
            return

        conns = await db.execute(
            select(Connection).where(
                or_(Connection.entry_a == eid, Connection.entry_b == eid)
            )
        )
        for conn in conns.scalars():
            other_id = conn.entry_b if conn.entry_a == eid else conn.entry_a
            edges.append({
                "id": str(conn.id),
                "source": str(conn.entry_a),
                "target": str(conn.entry_b),
                "type": conn.type.value,
                "strength": conn.strength,
            })
            await traverse(other_id, current_depth + 1)

    await traverse(entry_id, 1)
    return {"nodes": nodes, "edges": edges}


@router.post("/connections", response_model=ConnectionResponse, status_code=201)
async def create_connection(body: ConnectionCreate, db: AsyncSession = Depends(get_db)):
    conn = Connection(
        entry_a=body.entry_a,
        entry_b=body.entry_b,
        type=body.type,
        strength=body.strength,
        is_auto=False,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    logger.info("connection_created", entry_a=str(body.entry_a), entry_b=str(body.entry_b), type=body.type)
    return conn


@router.patch("/connections/{connection_id}", response_model=ConnectionResponse)
async def update_connection(connection_id: UUID, body: ConnectionUpdate, db: AsyncSession = Depends(get_db)):
    conn = await db.get(Connection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    if body.type is not None:     conn.type = body.type
    if body.strength is not None: conn.strength = body.strength
    await db.commit()
    await db.refresh(conn)
    return conn


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(connection_id: UUID, db: AsyncSession = Depends(get_db)):
    conn = await db.get(Connection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.delete(conn)
    await db.commit()


@router.get("/candidates")
async def list_candidates(status: str = "pending", db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(ConnectionCandidate).where(ConnectionCandidate.status == status).order_by(
            ConnectionCandidate.score.desc()
        ).limit(50)
    )
    candidates = rows.scalars().all()
    return [
        {
            "id": str(c.id),
            "entry_a": str(c.entry_a),
            "entry_b": str(c.entry_b),
            "score": c.score,
            "status": c.status,
        }
        for c in candidates
    ]


@router.post("/candidates/{candidate_id}", status_code=200)
async def act_on_candidate(
    candidate_id: UUID,
    body: CandidateAction,
    db: AsyncSession = Depends(get_db),
):
    cand = await db.get(ConnectionCandidate, candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if body.action == "approve":
        conn = Connection(
            entry_a=cand.entry_a,
            entry_b=cand.entry_b,
            type="related",
            strength=cand.score,
            is_auto=False,
        )
        db.add(conn)
        cand.status = "approved"
    elif body.action == "reject":
        cand.status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="action must be approve or reject")

    await db.commit()
    return {"status": cand.status}
