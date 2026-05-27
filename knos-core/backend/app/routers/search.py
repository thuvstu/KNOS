# backend/app/routers/search.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..schemas.entry import SearchQuery, SearchResponse
from ..services.search import hybrid_search

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(query: SearchQuery, db: AsyncSession = Depends(get_db)):
    return await hybrid_search(db, query)


@router.get("")
async def search_get(
    q: str = "",
    type: str = None,
    sort: str = "relevance",
    mode: str = "hybrid",
    offset: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    from ..models.entry import EntryType
    query = SearchQuery(
        q=q,
        type=EntryType(type) if type else None,
        sort=sort,
        mode=mode,
        offset=offset,
        limit=limit,
    )
    return await hybrid_search(db, query)
