-- supabase/migrations/001_init.sql
-- KnOS EX 初期マイグレーション

-- ─── Extensions ───
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Enums ───
CREATE TYPE post_type AS ENUM (
  'article',
  'note',
  'link',
  'knowledge',
  'question'
);

-- ─── profiles ───
CREATE TABLE profiles (
  id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL DEFAULT 'Anonymous',
  avatar_url   TEXT,
  bio          TEXT DEFAULT '',
  is_anon      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 新規ユーザー作成時にprofileを自動生成
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO profiles (id, display_name, is_anon)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', 'Anonymous'),
    (NEW.raw_app_meta_data->>'provider' = 'anonymous')
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ─── posts ───
CREATE TABLE posts (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type          post_type NOT NULL DEFAULT 'note',
  title         TEXT NOT NULL,
  content       TEXT NOT NULL DEFAULT '',
  source_url    TEXT NOT NULL DEFAULT '',
  user_id       UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  anon_name     TEXT NOT NULL DEFAULT 'Anonymous',
  tags          TEXT[] NOT NULL DEFAULT '{}',
  like_count    INTEGER NOT NULL DEFAULT 0,
  is_published  BOOLEAN NOT NULL DEFAULT TRUE,
  knos_entry_id TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- updated_at 自動更新トリガー
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER posts_updated_at
  BEFORE UPDATE ON posts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ─── likes ───
CREATE TABLE likes (
  post_id    UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (post_id, user_id)
);

-- like_count 同期トリガー
CREATE OR REPLACE FUNCTION sync_like_count()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE posts SET like_count = like_count + 1 WHERE id = NEW.post_id;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE posts SET like_count = GREATEST(like_count - 1, 0) WHERE id = OLD.post_id;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_like_change
  AFTER INSERT OR DELETE ON likes
  FOR EACH ROW EXECUTE FUNCTION sync_like_count();

-- ─── RLS ───
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts    ENABLE ROW LEVEL SECURITY;
ALTER TABLE likes    ENABLE ROW LEVEL SECURITY;

-- profiles
CREATE POLICY "profiles_select_all"   ON profiles FOR SELECT USING (true);
CREATE POLICY "profiles_update_own"   ON profiles FOR UPDATE USING (auth.uid() = id);

-- posts
CREATE POLICY "posts_select_published" ON posts FOR SELECT USING (is_published = TRUE);
CREATE POLICY "posts_insert_auth"      ON posts FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY "posts_update_own"       ON posts FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "posts_delete_own"       ON posts FOR DELETE USING (auth.uid() = user_id);

-- likes
CREATE POLICY "likes_select_all"  ON likes FOR SELECT USING (true);
CREATE POLICY "likes_insert_auth" ON likes FOR INSERT WITH CHECK (
  auth.uid() IS NOT NULL AND auth.uid() = user_id
);
CREATE POLICY "likes_delete_own"  ON likes FOR DELETE USING (auth.uid() = user_id);
