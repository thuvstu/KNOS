-- scripts/init.sql
-- KnOS Core 初期化スクリプト（Docker初回起動時に実行）

-- ─── Extensions ───
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgroonga";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- ─── entry_type enum ───
CREATE TYPE entry_type AS ENUM (
  'webpage', 'thought', 'book', 'video', 'document',
  'media', 'person', 'org', 'place', 'event',
  'definition', 'liked', 'ai_conv'
);

-- ─── connection_type enum ───
CREATE TYPE connection_type AS ENUM (
  'related', 'references', 'contradicts', 'extends',
  'exemplifies', 'authored_by', 'published_by',
  'located_at', 'occurred_at'
);

-- ─── entry (コアテーブル) ───
CREATE TABLE entry (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type         entry_type NOT NULL,
  title        TEXT NOT NULL DEFAULT '',
  content      TEXT NOT NULL DEFAULT '',
  source_url   TEXT NOT NULL DEFAULT '',
  lang         CHAR(10) NOT NULL DEFAULT 'ja',
  is_favorite  BOOLEAN NOT NULL DEFAULT FALSE,
  is_muted     BOOLEAN NOT NULL DEFAULT FALSE,
  metadata     JSONB NOT NULL DEFAULT '{}',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  accessed_at  TIMESTAMPTZ,
  deleted_at   TIMESTAMPTZ
);

CREATE INDEX idx_entry_type       ON entry(type) WHERE deleted_at IS NULL;
CREATE INDEX idx_entry_created_at ON entry(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_entry_favorite   ON entry(is_favorite) WHERE is_favorite AND deleted_at IS NULL;
CREATE INDEX idx_entry_deleted    ON entry(deleted_at) WHERE deleted_at IS NOT NULL;

-- PGroonga 全文検索インデックス
CREATE INDEX idx_entry_pgroonga ON entry
  USING pgroonga (title pgroonga_text_term_search_ops_v2,
                  content pgroonga_text_full_text_search_ops_v2);

-- updated_at トリガー
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER entry_updated_at
  BEFORE UPDATE ON entry
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ─── tag ───
CREATE TABLE tag (
  id         SERIAL PRIMARY KEY,
  name       TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE entry_tag (
  entry_id UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
  tag_id   INTEGER NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
  PRIMARY KEY (entry_id, tag_id)
);

CREATE INDEX idx_entry_tag_entry ON entry_tag(entry_id);
CREATE INDEX idx_entry_tag_tag   ON entry_tag(tag_id);

-- ─── topic ───
CREATE TABLE topic (
  id          SERIAL PRIMARY KEY,
  name        TEXT UNIQUE NOT NULL,
  parent_id   INTEGER REFERENCES topic(id) ON DELETE SET NULL,
  description TEXT DEFAULT '',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE entry_topic (
  entry_id UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
  topic_id INTEGER NOT NULL REFERENCES topic(id) ON DELETE CASCADE,
  PRIMARY KEY (entry_id, topic_id)
);

-- ─── embedding ───
CREATE TABLE embedding (
  entry_id  UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  vector    vector(768),  -- MRL截断 768次元 (gemini-embedding-2-preview)
  model     TEXT NOT NULL DEFAULT 'gemini-embedding-2-preview',
  input_text TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_embedding_vector ON embedding
  USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

-- ─── embedding_job ───
CREATE TABLE embedding_job (
  id         SERIAL PRIMARY KEY,
  entry_id   UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
  status     TEXT NOT NULL DEFAULT 'queued'
             CHECK (status IN ('queued', 'running', 'done', 'failed')),
  attempts   INTEGER NOT NULL DEFAULT 0,
  error_msg  TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_embedding_job_status ON embedding_job(status) WHERE status IN ('queued', 'running');

-- ─── connection ───
CREATE TABLE connection (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entry_a     UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
  entry_b     UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
  type        connection_type NOT NULL DEFAULT 'related',
  strength    FLOAT NOT NULL DEFAULT 1.0 CHECK (strength BETWEEN 0 AND 1),
  is_auto     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (entry_a, entry_b, type)
);

CREATE INDEX idx_connection_entry_a ON connection(entry_a);
CREATE INDEX idx_connection_entry_b ON connection(entry_b);

-- ─── connection_candidate ───
CREATE TABLE connection_candidate (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entry_a    UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
  entry_b    UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
  score      FLOAT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'pending'
             CHECK (status IN ('pending', 'approved', 'rejected')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (entry_a, entry_b)
);

-- ─── srs_review ───
CREATE TABLE srs_review (
  id          SERIAL PRIMARY KEY,
  entry_id    UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
  grade       INTEGER NOT NULL CHECK (grade BETWEEN 0 AND 5),
  ease_factor FLOAT NOT NULL DEFAULT 2.5,
  interval    INTEGER NOT NULL DEFAULT 1,
  next_review DATE NOT NULL,
  reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_srs_entry    ON srs_review(entry_id);
CREATE INDEX idx_srs_next     ON srs_review(next_review);

-- SRS 現在状態ビュー（最新レビューのみ）
CREATE VIEW srs_current AS
SELECT DISTINCT ON (entry_id)
  sr.*,
  e.title,
  e.content
FROM srs_review sr
JOIN entry e ON e.id = sr.entry_id
WHERE e.deleted_at IS NULL
  AND e.type = 'definition'
ORDER BY entry_id, reviewed_at DESC;

-- ─── 型別拡張テーブル ───

CREATE TABLE entry_webpage (
  entry_id     UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  url          TEXT NOT NULL DEFAULT '',
  domain       TEXT NOT NULL DEFAULT '',
  author       TEXT,
  published_at TIMESTAMPTZ,
  read_time_min INTEGER,
  is_read      BOOLEAN NOT NULL DEFAULT FALSE,
  summary      TEXT
);

CREATE TABLE entry_thought (
  entry_id  UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  mood      TEXT
);

CREATE TABLE entry_book (
  entry_id     UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  isbn         TEXT,
  author       TEXT,
  publisher    TEXT,
  published_at DATE,
  status       TEXT NOT NULL DEFAULT 'want'
               CHECK (status IN ('want', 'reading', 'done', 'dropped')),
  rating       INTEGER CHECK (rating BETWEEN 1 AND 5),
  started_at   DATE,
  finished_at  DATE
);

CREATE TABLE entry_video (
  entry_id     UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  url          TEXT NOT NULL DEFAULT '',
  platform     TEXT,
  channel      TEXT,
  duration_sec INTEGER,
  watched_at   TIMESTAMPTZ,
  transcript   TEXT
);

CREATE TABLE entry_document (
  entry_id    UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  file_path   TEXT,
  mime_type   TEXT,
  pages       INTEGER,
  file_size   BIGINT,
  ocr_done    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE entry_person (
  entry_id    UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  name_en     TEXT,
  name_ja     TEXT,
  affiliation TEXT,
  bio         TEXT,
  url         TEXT
);

CREATE TABLE entry_org (
  entry_id    UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  name_en     TEXT,
  url         TEXT,
  industry    TEXT
);

CREATE TABLE entry_place (
  entry_id    UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  address     TEXT,
  lat         DOUBLE PRECISION,
  lng         DOUBLE PRECISION,
  geom        geometry(Point, 4326),
  category    TEXT,
  visited_at  TIMESTAMPTZ
);

CREATE INDEX idx_entry_place_geom ON entry_place USING GIST (geom);

CREATE TABLE entry_event (
  entry_id    UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  occurred_at TIMESTAMPTZ,
  ended_at    TIMESTAMPTZ,
  location    TEXT,
  score       FLOAT
);

CREATE TABLE entry_definition (
  entry_id    UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  term        TEXT NOT NULL,
  definition  TEXT NOT NULL,
  example     TEXT,
  source      TEXT
);

CREATE TABLE entry_liked (
  entry_id    UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  platform    TEXT,
  original_id TEXT,
  liked_at    TIMESTAMPTZ,
  author      TEXT,
  body_text   TEXT
);

CREATE TABLE entry_ai_conv (
  entry_id    UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
  model       TEXT,
  messages    JSONB NOT NULL DEFAULT '[]',
  token_count INTEGER
);
