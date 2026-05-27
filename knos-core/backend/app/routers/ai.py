# backend/app/routers/ai.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional, AsyncGenerator
import json
import structlog

from ..database import get_db
from ..models.entry import Entry
from ..services.search import hybrid_search
from ..schemas.entry import SearchQuery
from ..config import get_settings

logger = structlog.get_logger()
router = APIRouter(prefix="/ai", tags=["ai"])
settings = get_settings()

MAX_CONTEXT_CHARS = 12000


# ─── /ai/ask  ───────────────────────────────────────────────
@router.post("/ask")
async def ask(
    question: str,
    entry_ids: Optional[list[str]] = None,
    use_search: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    KnOS内のエントリーをコンテキストにしてGeminiに質問を投げる。
    use_search=true の場合はハイブリッド検索で自動的に関連エントリーを取得。
    """
    context_entries: list[dict] = []

    if entry_ids:
        for eid in entry_ids:
            try:
                e = await db.get(Entry, UUID(eid))
                if e and not e.deleted_at:
                    context_entries.append({"title": e.title, "content": e.content[:2000]})
            except Exception:
                continue

    if use_search and not context_entries:
        search_resp = await hybrid_search(
            db,
            SearchQuery(q=question, limit=5, mode="hybrid"),
        )
        for result in search_resp.results:
            context_entries.append({
                "title": result.entry.title,
                "content": result.entry.content[:2000],
            })

    context_text = ""
    for i, entry in enumerate(context_entries, 1):
        context_text += f"[{i}] {entry['title']}\n{entry['content']}\n\n"
        if len(context_text) > MAX_CONTEXT_CHARS:
            break

    prompt = f"""以下はユーザーの個人知識ベース（KnOS）の関連エントリーです:

{context_text}
---
上記のコンテキストを参考にして、以下の質問に日本語で答えてください:
{question}
"""

    if settings.gemini_api_key:
        answer = await _ask_gemini(prompt)
    elif settings.ollama_base_url:
        answer = await _ask_ollama(prompt)
    else:
        answer = "⚠ AI設定がありません。GEMINI_API_KEY または OLLAMA_BASE_URL を設定してください。"

    return {
        "answer": answer,
        "context_count": len(context_entries),
        "sources": [e["title"] for e in context_entries],
    }


# ─── /ai/ask/stream  ────────────────────────────────────────
@router.post("/ask/stream")
async def ask_stream(
    question: str,
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events でストリーミング回答"""

    async def generate() -> AsyncGenerator[str, None]:
        search_resp = await hybrid_search(
            db, SearchQuery(q=question, limit=5, mode="hybrid")
        )
        context_text = ""
        for result in search_resp.results:
            context_text += f"- {result.entry.title}: {result.entry.content[:800]}\n\n"

        prompt = f"コンテキスト:\n{context_text}\n\n質問: {question}"

        if settings.gemini_api_key:
            async for chunk in _stream_gemini(prompt):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        else:
            yield f"data: {json.dumps({'chunk': '⚠ GEMINI_API_KEY が設定されていません'})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ─── /ai/summarize  ─────────────────────────────────────────
@router.post("/summarize/{entry_id}")
async def summarize_entry(entry_id: UUID, db: AsyncSession = Depends(get_db)):
    entry = await db.get(Entry, entry_id)
    if not entry or entry.deleted_at:
        raise HTTPException(status_code=404, detail="Entry not found")

    if not entry.content:
        raise HTTPException(status_code=400, detail="Entry has no content")

    prompt = f"""以下のテキストを3行以内の日本語で要約してください:

タイトル: {entry.title}
内容:
{entry.content[:4000]}
"""

    if settings.gemini_api_key:
        summary = await _ask_gemini(prompt)
    else:
        summary = entry.content[:200] + "..."

    return {"entry_id": str(entry_id), "summary": summary}


# ─── /ai/suggest-connections  ───────────────────────────────
@router.post("/suggest-connections/{entry_id}")
async def suggest_connections(entry_id: UUID, db: AsyncSession = Depends(get_db)):
    """LLMを使って接続候補の説明文を生成"""
    from ..services.connection import generate_connection_candidates
    from ..models.entry import ConnectionCandidate
    from sqlalchemy import or_

    count = await generate_connection_candidates(db, entry_id)

    candidates = (await db.execute(
        select(ConnectionCandidate).where(
            or_(
                ConnectionCandidate.entry_a == entry_id,
                ConnectionCandidate.entry_b == entry_id,
            ),
            ConnectionCandidate.status == "pending",
        ).order_by(ConnectionCandidate.score.desc()).limit(5)
    )).scalars().all()

    results = []
    for c in candidates:
        other_id = c.entry_b if c.entry_a == entry_id else c.entry_a
        other = await db.get(Entry, other_id)
        if other:
            results.append({
                "candidate_id": str(c.id),
                "other_id": str(other_id),
                "other_title": other.title,
                "score": c.score,
            })

    return {"generated_candidates": count, "top_candidates": results}


# ─── helpers ────────────────────────────────────────────────

async def _ask_gemini(prompt: str) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.llm_model)
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logger.error("gemini_ask_failed", error=str(e))
        return f"エラー: {e}"


async def _stream_gemini(prompt: str) -> AsyncGenerator[str, None]:
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.llm_model)
        async for chunk in await model.generate_content_async(prompt, stream=True):
            yield chunk.text
    except Exception as e:
        yield f"エラー: {e}"


async def _ask_ollama(prompt: str) -> str:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
    except Exception as e:
        logger.error("ollama_ask_failed", error=str(e))
        return f"エラー: {e}"
