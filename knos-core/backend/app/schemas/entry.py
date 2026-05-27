# backend/app/schemas/entry.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime, date
from uuid import UUID
from ..models.entry import EntryType, ConnectionType


class TagSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class TopicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    parent_id: Optional[int] = None


# ─── Entry CRUD ───

class EntryCreate(BaseModel):
    type: EntryType
    title: str = ""
    content: str = ""
    source_url: str = ""
    lang: str = "ja"
    tags: list[str] = []
    metadata: dict[str, Any] = {}
    # 型別拡張（任意）
    ext: Optional[dict[str, Any]] = None


class EntryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    source_url: Optional[str] = None
    lang: Optional[str] = None
    is_favorite: Optional[bool] = None
    is_muted: Optional[bool] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None
    ext: Optional[dict[str, Any]] = None


class EntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: EntryType
    title: str
    content: str
    source_url: str
    lang: str
    is_favorite: bool
    is_muted: bool
    metadata_: dict[str, Any] = Field(alias="metadata_", default={})
    created_at: datetime
    updated_at: datetime
    accessed_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    tags: list[TagSchema] = []
    topics: list[TopicSchema] = []
    has_embedding: bool = False

    model_config = ConfigDict(populate_by_name=True)


class EntryListResponse(BaseModel):
    items: list[EntryResponse]
    total: int
    offset: int
    limit: int


# ─── Search ───

class SearchQuery(BaseModel):
    q: str = ""
    type: Optional[EntryType] = None
    tags: list[str] = []
    topic_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sort: str = "relevance"  # relevance | created_at | updated_at
    offset: int = 0
    limit: int = 20
    mode: str = "hybrid"  # hybrid | fulltext | semantic


class SearchResult(BaseModel):
    entry: EntryResponse
    score: float
    highlight: Optional[str] = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    timing_ms: dict[str, float]


# ─── Connection ───

class ConnectionCreate(BaseModel):
    entry_a: UUID
    entry_b: UUID
    type: ConnectionType = ConnectionType.related
    strength: float = Field(default=1.0, ge=0.0, le=1.0)


class ConnectionUpdate(BaseModel):
    type: Optional[ConnectionType] = None
    strength: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    entry_a: UUID
    entry_b: UUID
    type: ConnectionType
    strength: float
    is_auto: bool
    created_at: datetime


class CandidateAction(BaseModel):
    action: str  # approve | reject


# ─── SRS ───

class SrsReviewCreate(BaseModel):
    grade: int = Field(ge=0, le=5)


class SrsReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entry_id: UUID
    grade: int
    ease_factor: float
    interval: int
    next_review: date
    reviewed_at: datetime


# ─── Import ───

class ImportUrlRequest(BaseModel):
    url: str
    tags: list[str] = []


class ImportFileResponse(BaseModel):
    entry_id: UUID
    title: str
    pages: Optional[int] = None
