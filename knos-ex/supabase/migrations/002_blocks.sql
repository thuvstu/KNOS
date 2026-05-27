-- supabase/migrations/002_blocks.sql
-- ブロックエディター対応マイグレーション

-- ─── posts にブロックカラムを追加 ───
ALTER TABLE posts ADD COLUMN IF NOT EXISTS blocks      JSONB;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS blocks_text TEXT;

-- ─── インデックス ───
CREATE INDEX IF NOT EXISTS idx_posts_title_trgm
  ON posts USING gin (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_posts_content_trgm
  ON posts USING gin (content gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_posts_blocks_text
  ON posts USING gin (blocks_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_posts_tags
  ON posts USING gin (tags);

CREATE INDEX IF NOT EXISTS idx_posts_created_at
  ON posts (created_at DESC) WHERE is_published;

CREATE INDEX IF NOT EXISTS idx_posts_user_id
  ON posts (user_id) WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_posts_blocks
  ON posts USING gin (blocks) WHERE blocks IS NOT NULL;

-- ─── post_block_tags ───
CREATE TABLE post_block_tags (
  post_id   UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  block_id  TEXT NOT NULL,
  tag       TEXT NOT NULL,
  PRIMARY KEY (post_id, block_id, tag)
);

CREATE INDEX idx_pbt_tag     ON post_block_tags(tag);
CREATE INDEX idx_pbt_post_id ON post_block_tags(post_id);

-- RLS
ALTER TABLE post_block_tags ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pbt_select_all" ON post_block_tags FOR SELECT USING (true);

CREATE POLICY "pbt_insert_owner" ON post_block_tags FOR INSERT WITH CHECK (
  EXISTS (
    SELECT 1 FROM posts
    WHERE id = post_id AND user_id = auth.uid()
  )
);

CREATE POLICY "pbt_delete_owner" ON post_block_tags FOR DELETE USING (
  EXISTS (
    SELECT 1 FROM posts
    WHERE id = post_id AND user_id = auth.uid()
  )
);

-- ─── tag_counts ビュー ───
CREATE OR REPLACE VIEW tag_counts AS
SELECT
  tag,
  COUNT(*) AS post_count
FROM posts, unnest(tags) AS tag
WHERE is_published = TRUE
GROUP BY tag
ORDER BY post_count DESC;

-- ─── sync_block_tags RPC ───
-- [{blockId: string, tags: string[]}] 形式のJSONB を受け取り、
-- post_block_tags を全件置き換えし、posts.tags にマージする
CREATE OR REPLACE FUNCTION sync_block_tags(
  p_post_id   UUID,
  p_block_tags JSONB
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  entry     JSONB;
  block_id  TEXT;
  tag_val   TEXT;
  new_tags  TEXT[];
BEGIN
  -- 既存のブロックタグを削除
  DELETE FROM post_block_tags WHERE post_id = p_post_id;

  -- 新しいブロックタグを挿入
  FOR entry IN SELECT * FROM jsonb_array_elements(p_block_tags)
  LOOP
    block_id := entry->>'blockId';
    FOR tag_val IN SELECT jsonb_array_elements_text(entry->'tags')
    LOOP
      INSERT INTO post_block_tags (post_id, block_id, tag)
      VALUES (p_post_id, block_id, tag_val)
      ON CONFLICT DO NOTHING;
    END LOOP;
  END LOOP;

  -- posts.tags にブロックタグをマージ
  SELECT array_agg(DISTINCT tag)
  INTO new_tags
  FROM (
    SELECT unnest(tags) AS tag FROM posts WHERE id = p_post_id
    UNION
    SELECT tag FROM post_block_tags WHERE post_id = p_post_id
  ) t;

  UPDATE posts
  SET tags = COALESCE(new_tags, '{}')
  WHERE id = p_post_id;
END;
$$;
