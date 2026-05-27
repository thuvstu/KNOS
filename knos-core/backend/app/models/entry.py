# backend/app/models/entry.py
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, BigInteger,
    DateTime, Date, ForeignKey, Enum, CheckConstraint, UniqueConstraint,
    Index, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from geoalchemy2 import Geometry
from datetime import datetime
import enum
import uuid

from ..database import Base


class EntryType(str, enum.Enum):
    webpage    = "webpage"
    thought    = "thought"
    book       = "book"
    video      = "video"
    document   = "document"
    media      = "media"
    person     = "person"
    org        = "org"
    place      = "place"
    event      = "event"
    definition = "definition"
    liked      = "liked"
    ai_conv    = "ai_conv"


class ConnectionType(str, enum.Enum):
    related      = "related"
    references   = "references"
    contradicts  = "contradicts"
    extends      = "extends"
    exemplifies  = "exemplifies"
    authored_by  = "authored_by"
    published_by = "published_by"
    located_at   = "located_at"
    occurred_at  = "occurred_at"


class Entry(Base):
    __tablename__ = "entry"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type        = Column(Enum(EntryType, name="entry_type"), nullable=False)
    title       = Column(Text, nullable=False, default="")
    content     = Column(Text, nullable=False, default="")
    source_url  = Column(Text, nullable=False, default="")
    lang        = Column(String(10), nullable=False, default="ja")
    is_favorite = Column(Boolean, nullable=False, default=False)
    is_muted    = Column(Boolean, nullable=False, default=False)
    metadata_   = Column("metadata", JSONB, nullable=False, default=dict)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    accessed_at = Column(DateTime(timezone=True))
    deleted_at  = Column(DateTime(timezone=True))

    # Relationships
    tags        = relationship("Tag", secondary="entry_tag", back_populates="entries", lazy="selectin")
    topics      = relationship("Topic", secondary="entry_topic", back_populates="entries", lazy="selectin")
    embedding   = relationship("Embedding", back_populates="entry", uselist=False, lazy="selectin")
    srs_reviews = relationship("SrsReview", back_populates="entry", order_by="SrsReview.reviewed_at.desc()")

    connections_a = relationship("Connection", foreign_keys="Connection.entry_a", back_populates="entry_a_obj")
    connections_b = relationship("Connection", foreign_keys="Connection.entry_b", back_populates="entry_b_obj")


class Tag(Base):
    __tablename__ = "tag"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(Text, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    entries = relationship("Entry", secondary="entry_tag", back_populates="tags")


class EntryTag(Base):
    __tablename__ = "entry_tag"
    entry_id = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    tag_id   = Column(Integer, ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)


class Topic(Base):
    __tablename__ = "topic"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(Text, unique=True, nullable=False)
    parent_id   = Column(Integer, ForeignKey("topic.id", ondelete="SET NULL"))
    description = Column(Text, default="")
    created_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    parent   = relationship("Topic", remote_side="Topic.id")
    children = relationship("Topic")
    entries  = relationship("Entry", secondary="entry_topic", back_populates="topics")


class EntryTopic(Base):
    __tablename__ = "entry_topic"
    entry_id = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    topic_id = Column(Integer, ForeignKey("topic.id", ondelete="CASCADE"), primary_key=True)


class Embedding(Base):
    __tablename__ = "embedding"

    entry_id   = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    vector     = Column(Vector(768))
    model      = Column(Text, nullable=False, default="gemini-embedding-2-preview")
    input_text = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    entry = relationship("Entry", back_populates="embedding")


class EmbeddingJob(Base):
    __tablename__ = "embedding_job"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    entry_id   = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), nullable=False)
    status     = Column(Text, nullable=False, default="queued")
    attempts   = Column(Integer, nullable=False, default=0)
    error_msg  = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    entry = relationship("Entry")


class Connection(Base):
    __tablename__ = "connection"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_a    = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), nullable=False)
    entry_b    = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), nullable=False)
    type       = Column(Enum(ConnectionType, name="connection_type"), nullable=False, default=ConnectionType.related)
    strength   = Column(Float, nullable=False, default=1.0)
    is_auto    = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    entry_a_obj = relationship("Entry", foreign_keys=[entry_a], back_populates="connections_a")
    entry_b_obj = relationship("Entry", foreign_keys=[entry_b], back_populates="connections_b")

    __table_args__ = (UniqueConstraint("entry_a", "entry_b", "type"),)


class ConnectionCandidate(Base):
    __tablename__ = "connection_candidate"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_a    = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), nullable=False)
    entry_b    = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), nullable=False)
    score      = Column(Float, nullable=False)
    status     = Column(Text, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("entry_a", "entry_b"),)


class SrsReview(Base):
    __tablename__ = "srs_review"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    entry_id    = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), nullable=False)
    grade       = Column(Integer, nullable=False)
    ease_factor = Column(Float, nullable=False, default=2.5)
    interval    = Column(Integer, nullable=False, default=1)
    next_review = Column(Date, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    entry = relationship("Entry", back_populates="srs_reviews")


# ─── Extension tables ───

class EntryWebpage(Base):
    __tablename__ = "entry_webpage"
    entry_id       = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    url            = Column(Text, nullable=False, default="")
    domain         = Column(Text, nullable=False, default="")
    author         = Column(Text)
    published_at   = Column(DateTime(timezone=True))
    read_time_min  = Column(Integer)
    is_read        = Column(Boolean, nullable=False, default=False)
    summary        = Column(Text)


class EntryThought(Base):
    __tablename__ = "entry_thought"
    entry_id = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    mood     = Column(Text)


class EntryBook(Base):
    __tablename__ = "entry_book"
    entry_id     = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    isbn         = Column(Text)
    author       = Column(Text)
    publisher    = Column(Text)
    published_at = Column(Date)
    status       = Column(Text, nullable=False, default="want")
    rating       = Column(Integer)
    started_at   = Column(Date)
    finished_at  = Column(Date)


class EntryVideo(Base):
    __tablename__ = "entry_video"
    entry_id     = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    url          = Column(Text, nullable=False, default="")
    platform     = Column(Text)
    channel      = Column(Text)
    duration_sec = Column(Integer)
    watched_at   = Column(DateTime(timezone=True))
    transcript   = Column(Text)


class EntryDocument(Base):
    __tablename__ = "entry_document"
    entry_id  = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    file_path = Column(Text)
    mime_type = Column(Text)
    pages     = Column(Integer)
    file_size = Column(BigInteger)
    ocr_done  = Column(Boolean, nullable=False, default=False)


class EntryPerson(Base):
    __tablename__ = "entry_person"
    entry_id    = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    name_en     = Column(Text)
    name_ja     = Column(Text)
    affiliation = Column(Text)
    bio         = Column(Text)
    url         = Column(Text)


class EntryOrg(Base):
    __tablename__ = "entry_org"
    entry_id = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    name_en  = Column(Text)
    url      = Column(Text)
    industry = Column(Text)


class EntryPlace(Base):
    __tablename__ = "entry_place"
    entry_id   = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    address    = Column(Text)
    lat        = Column(Float)
    lng        = Column(Float)
    geom       = Column(Geometry("POINT", srid=4326))
    category   = Column(Text)
    visited_at = Column(DateTime(timezone=True))


class EntryEvent(Base):
    __tablename__ = "entry_event"
    entry_id    = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    occurred_at = Column(DateTime(timezone=True))
    ended_at    = Column(DateTime(timezone=True))
    location    = Column(Text)
    score       = Column(Float)


class EntryDefinition(Base):
    __tablename__ = "entry_definition"
    entry_id   = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    term       = Column(Text, nullable=False)
    definition = Column(Text, nullable=False)
    example    = Column(Text)
    source     = Column(Text)


class EntryLiked(Base):
    __tablename__ = "entry_liked"
    entry_id    = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    platform    = Column(Text)
    original_id = Column(Text)
    liked_at    = Column(DateTime(timezone=True))
    author      = Column(Text)
    body_text   = Column(Text)


class EntryAiConv(Base):
    __tablename__ = "entry_ai_conv"
    entry_id    = Column(UUID(as_uuid=True), ForeignKey("entry.id", ondelete="CASCADE"), primary_key=True)
    model       = Column(Text)
    messages    = Column(JSONB, nullable=False, default=list)
    token_count = Column(Integer)
