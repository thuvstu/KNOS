# KnOS EX — 完全仕様書

**バージョン:** 1.0  
**作成日:** 2026-05-23  
**ステータス:** 実装中

---

## 目次

1. [プロジェクト概要](#1-プロジェクト概要)
2. [技術スタック](#2-技術スタック)
3. [インフラ・デプロイ構成](#3-インフラデプロイ構成)
4. [データベース設計](#4-データベース設計)
5. [機能仕様](#5-機能仕様)
6. [リッチエディター仕様](#6-リッチエディター仕様)
7. [ファイル構成](#7-ファイル構成)
8. [画面設計](#8-画面設計)
9. [API・RPCインターフェース](#9-apirpcインターフェース)
10. [セキュリティ（RLS）](#10-セキュリティrls)
11. [セットアップ手順](#11-セットアップ手順)
12. [開発フェーズ](#12-開発フェーズ)

---

## 1. プロジェクト概要

### 1.1 一文定義

誰でも・ログイン不要で・どんなコンテンツでも投稿できる、ブロック単位の自由度を持つ知識共有プラットフォーム。

### 1.2 特徴

- **匿名投稿 OR OAuth ログイン** — 登録不要でその場で投稿可能
- **ブロックベースエディター** — どこにでも何個でもコンテンツブロックを配置
- **ブロック単位のタグ付け** — 投稿全体だけでなく各ブロックにタグを付けて検索可能
- **KaTeX 数式** — インライン `$...$` / ブロック `$$...$$` 両対応
- **コードブロック** — 10言語シンタックスハイライト + ワンクリックコピー
- **動画埋め込み** — YouTube / Vimeo URL から自動変換
- **Callout ブロック** — info / tip / warning / danger
- **折りたたみブロック** — details/summary
- **テーブル** — リサイズ可能
- **スラッシュコマンド** — `/` を打つとブロック挿入メニュー
- **KnOS 連携** — `knos_entry_id` で個人 KnOS のエントリーとリンク可能（将来）

### 1.3 スコープ外

- 課金・有料プラン
- コメント機能（将来フェーズで追加可）
- リアルタイム共同編集
- 独自ドメインのユーザーページ（将来）

---

## 2. 技術スタック

### 2.1 フロントエンド

| 項目 | 選択 | バージョン |
|------|------|-----------|
| フレームワーク | Next.js (App Router) | 16.2.4 |
| UI ライブラリ | React | ^19.2.0 |
| スタイリング | Tailwind CSS v4 | ^4.1.0 |
| タイポグラフィ | @tailwindcss/typography | ^0.5.15 |
| エディター | Tiptap | ^2.10.3 |
| 数式 | KaTeX | ^0.16.11 |
| シンタックスHL | lowlight + highlight.js | ^3.2.0 |
| アイコン | lucide-react | ^0.507.0 |
| ユーティリティ | clsx + tailwind-merge | ^2.x |

### 2.2 バックエンド / DB

| 項目 | 選択 |
|------|------|
| BaaS | Supabase（無料枠） |
| DB | PostgreSQL 15（Supabase管理） |
| 認証 | Supabase Auth（匿名 + Google OAuth + GitHub OAuth） |
| ストレージ | Supabase Storage（画像アップロード・将来） |
| 全文検索 | pg_trgm（GINインデックス） |

### 2.3 インフラ

| 項目 | 選択 |
|------|------|
| ホスティング | Vercel（無料枠） |
| DB/Auth | Supabase（無料枠） |
| 費用 | 完全無料（クレジットカード不要） |

---

## 3. インフラ・デプロイ構成

```
ユーザー（ブラウザ / スマホ）
    ↓ HTTPS
Vercel CDN
    ↓ SSR / API Routes
Next.js App (Vercel Edge/Node)
    ↓ Supabase JS Client
Supabase
    ├── PostgreSQL（posts, profiles, likes, post_block_tags）
    ├── Auth（匿名セッション / Google / GitHub）
    └── Storage（将来: 画像アップロード）
```

### 3.1 環境変数（`.env.local`）

```env
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...
NEXT_PUBLIC_SITE_URL=https://your-app.vercel.app
```

---

## 4. データベース設計

### 4.1 テーブル一覧

| テーブル | 説明 |
|---------|------|
| `profiles` | ユーザープロフィール（Supabase Auth連動） |
| `posts` | 投稿（本体） |
| `likes` | いいね（1ユーザー1いいね） |
| `post_block_tags` | ブロック単位のタグ |

### 4.2 `post_type` enum

```sql
CREATE TYPE post_type AS ENUM (
  'article',    -- 長文記事
  'note',       -- 短いメモ・TIL
  'link',       -- URLシェア
  'knowledge',  -- KnOSからの公開エクスポート
  'question'    -- 質問
);
```

### 4.3 `profiles`

```sql
CREATE TABLE profiles (
  id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL DEFAULT 'Anonymous',
  avatar_url   TEXT,
  bio          TEXT DEFAULT '',
  is_anon      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

新規ユーザー作成時に `handle_new_user()` トリガーで自動生成。

### 4.4 `posts`

```sql
CREATE TABLE posts (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type          post_type NOT NULL DEFAULT 'note',
  title         TEXT NOT NULL,
  content       TEXT NOT NULL DEFAULT '',      -- プレーンテキスト（全文検索用）
  blocks        JSONB,                          -- Tiptap JSONドキュメント
  blocks_text   TEXT,                           -- ブロック全文（全文検索用）
  source_url    TEXT NOT NULL DEFAULT '',       -- linkタイプ用URL
  user_id       UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  anon_name     TEXT NOT NULL DEFAULT 'Anonymous',
  tags          TEXT[] NOT NULL DEFAULT '{}',   -- 投稿レベルタグ
  like_count    INTEGER NOT NULL DEFAULT 0,
  is_published  BOOLEAN NOT NULL DEFAULT TRUE,
  knos_entry_id TEXT,                           -- KnOS Phase1連携用
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**インデックス:**
```sql
-- 全文検索
CREATE INDEX idx_posts_title_trgm   ON posts USING gin (title   gin_trgm_ops);
CREATE INDEX idx_posts_content_trgm ON posts USING gin (content gin_trgm_ops);
CREATE INDEX idx_posts_blocks_text  ON posts USING gin (blocks_text gin_trgm_ops);
-- フィルタ・ソート
CREATE INDEX idx_posts_tags         ON posts USING gin (tags);
CREATE INDEX idx_posts_created_at   ON posts (created_at DESC) WHERE is_published;
CREATE INDEX idx_posts_user_id      ON posts (user_id) WHERE user_id IS NOT NULL;
-- JSONB
CREATE INDEX idx_posts_blocks       ON posts USING gin (blocks) WHERE blocks IS NOT NULL;
```

`like_count` は `sync_like_count()` トリガーで `likes` テーブルと自動同期。  
`updated_at` は `update_updated_at()` トリガーで自動更新。

### 4.5 `likes`

```sql
CREATE TABLE likes (
  post_id    UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (post_id, user_id)
);
```

### 4.6 `post_block_tags`

ブロック単位のタグ。Tiptapノードの `blockId` 属性で紐付ける。

```sql
CREATE TABLE post_block_tags (
  post_id   UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  block_id  TEXT NOT NULL,   -- Tiptapノードのblockid属性値
  tag       TEXT NOT NULL,
  PRIMARY KEY (post_id, block_id, tag)
);

CREATE INDEX idx_pbt_tag     ON post_block_tags(tag);
CREATE INDEX idx_pbt_post_id ON post_block_tags(post_id);
```

### 4.7 ビュー

```sql
-- 人気タグ集計
CREATE VIEW tag_counts AS
SELECT tag, COUNT(*) AS post_count
FROM posts, unnest(tags) AS tag
WHERE is_published
GROUP BY tag
ORDER BY post_count DESC;
```

### 4.8 RPC関数

```sql
-- ブロックタグの一括同期
CREATE OR REPLACE FUNCTION sync_block_tags(
  p_post_id UUID,
  p_block_tags JSONB  -- [{blockId: string, tags: string[]}]
) RETURNS void ...
```

---

## 5. 機能仕様

### 5.1 認証フロー

| パターン | 動作 |
|---------|------|
| 未ログインで投稿 | `signInAnonymously()` で匿名ユーザーを自動生成し投稿 |
| Google ログイン | `signInWithOAuth({ provider: 'google' })` |
| GitHub ログイン | `signInWithOAuth({ provider: 'github' })` |
| ログアウト | `signOut()` |

匿名ユーザーは `profiles.is_anon = TRUE`。表示名は `anon_name` カラムから取得。

### 5.2 投稿タイプ

| 値 | 日本語 | 用途 |
|----|--------|------|
| `article` | 記事 | 長文・まとまった知識 |
| `note` | メモ | 短いメモ・TIL・思考 |
| `link` | リンク | URL共有 + コメント |
| `knowledge` | 知識 | KnOS公開エクスポート |
| `question` | 質問 | 質問・相談 |

### 5.3 タグシステム

**3層のタグ:**

1. **投稿タグ** (`posts.tags TEXT[]`) — 投稿全体に付くタグ
2. **ブロックタグ** (`post_block_tags`) — 各ブロックに付くタグ。投稿タグに自動マージ
3. **ブロック属性タグ** (`data-block-tags` 属性) — Tiptap JSONに埋め込み、エディターで視覚表示

ブロックタグは投稿時に `sync_block_tags()` RPC で DB に同期される。

### 5.4 いいね

- 1ユーザー1投稿1いいね（`likes` テーブルのPK制約）
- 未ログインでいいねしようとすると匿名ログインを実行
- `like_count` はトリガーで即時更新
- UIは楽観的更新（即座に数字を変更してからAPI呼び出し）

### 5.5 検索・フィルター

| 機能 | 実装 |
|------|------|
| キーワード検索 | `title ILIKE` + `content ILIKE` + `blocks_text ILIKE` |
| タイプフィルター | `type = ?` |
| タグフィルター | `tags @> ARRAY[?]` |
| ソート | `created_at DESC`（固定・将来: like_count DESC 追加） |
| ページネーション | LIMIT 30（将来: 無限スクロール） |

---

## 6. リッチエディター仕様

### 6.1 使用ライブラリ

- **Tiptap 2.x** — ProseMirrorベースのヘッドレスエディター
- **StarterKit** — 基本ブロック群（paragraph, heading, bold, italic, etc.）
- **KaTeX** — 数式レンダリング
- **lowlight** — コードシンタックスハイライト（サーバー・クライアント両対応）

### 6.2 対応ブロック一覧

| ブロック | 挿入方法 | 説明 |
|---------|---------|------|
| 段落 | デフォルト | 通常テキスト |
| 見出し H1〜H4 | `/h1` `/h2` `/h3` or ツールバー | 階層見出し |
| 太字 | `**...**` or ⌘B | |
| 斜体 | `*...*` or ⌘I | |
| 下線 | ⌘U | |
| 取り消し線 | `~~...~~` | |
| インラインコード | `` `...` `` | |
| 上付き文字 | ツールバー | `x²` |
| 下付き文字 | ツールバー | `H₂O` |
| 箇条書き | `/bullet` or `-` + Space | |
| 番号リスト | `/ordered` or `1.` + Space | |
| チェックリスト | `/task` or `[ ]` + Space | チェック可能 |
| 引用 | `/quote` or `>` + Space | |
| 区切り線 | `/divider` or `---` | |
| **コードブロック** | `/code` or ` ``` ` + Enter | シンタックスHL + コピーボタン |
| **数式ブロック** | `/math` or ⌘⇧M | KaTeX ブロック数式 |
| **インライン数式** | `$...$` | KaTeX インライン |
| **テーブル** | `/table` | 3×3、リサイズ可 |
| **画像** | `/image` or ツールバー | URL指定 |
| **動画埋め込み** | `/video` or ツールバー | YouTube/Vimeo 自動embed |
| **Callout (info)** | `/info` | ℹ️ 情報ボックス |
| **Callout (tip)** | `/tip` | 💡 ヒントボックス |
| **Callout (warning)** | `/warning` | ⚠️ 警告ボックス |
| **Callout (danger)** | `/danger` | 🚨 危険ボックス |
| **折りたたみ** | `/details` | details/summary |
| リンク | ⌘K or ツールバー | 外部リンク |

### 6.3 テキスト装飾

| 装飾 | 方法 |
|------|------|
| 文字色 | ツールバー → カラーパレット（8色） |
| ハイライト | ツールバー → ハイライトパレット（6色） |
| テキスト配置 | 左/中央/右 |

### 6.4 スラッシュコマンド

`/` を入力するとコマンドメニューが表示される。

- 入力続きでインクリメンタルフィルタリング
- ↑↓キーで選択、Enter で実行、Escape で閉じる
- マウスクリックでも選択可能
- 最大10件表示

### 6.5 ブロックタグ付け

1. タグを付けたいブロック内をクリック
2. ツールバーの 🏷 ボタンをクリック → BlockTagPanel が展開
3. タグを入力して Enter / 追加ボタン
4. ブロックに `data-block-tags` 属性として保存
5. エディター内でタグが視覚的に表示される（`::after` 疑似要素）
6. 投稿時に `post_block_tags` テーブルに同期 + `posts.tags` に自動マージ

### 6.6 コードブロック対応言語

javascript, typescript, python, rust, go, sql, bash, css, json, xml/html

### 6.7 KaTeX 数式例

```
インライン: $E = mc^2$
ブロック:
$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$
```

### 6.8 コードブロック コピーボタン

`BlockRenderer` のクライアントサイド `useEffect` で `pre` タグに動的追加。  
コピー後2秒間「copied!」表示。

### 6.9 カスタム Tiptap 拡張

| 拡張名 | ファイル | 説明 |
|--------|---------|------|
| `BlockId` | `extensions.ts` | 全ブロックに UUID を自動付与 |
| `MathInline` | `extensions.ts` | `$...$` インライン数式 |
| `MathBlock` | `extensions.ts` | `$$...$$` ブロック数式 |
| `Callout` | `extensions.ts` | info/tip/warning/danger ブロック |
| `Video` | `extensions.ts` | YouTube/Vimeo 埋め込み |
| `SlashCommand` | `SlashCommand.ts` | `/` コマンドメニュー |

---

## 7. ファイル構成

```
knos-ex/
│
├── app/
│   ├── globals.css              ← Tailwind v4 + エディタースタイル全体
│   ├── layout.tsx               ← ルートレイアウト（NavBar含む）
│   ├── page.tsx                 ← フィードページ（SSR）
│   ├── new/
│   │   └── page.tsx             ← 投稿作成（RichEditor統合）
│   ├── post/
│   │   └── [id]/
│   │       └── page.tsx         ← 投稿詳細（BlockRenderer）
│   └── auth/
│       └── callback/
│           └── route.ts         ← OAuth コールバック
│
├── components/
│   ├── NavBar.tsx               ← ナビゲーション + 認証UI
│   ├── PostCard.tsx             ← フィードのカード（いいね含む）
│   ├── FeedFilter.tsx           ← 検索・タグ・タイプフィルター
│   └── editor/
│       ├── RichEditor.tsx       ← メインエディターコンポーネント
│       ├── Toolbar.tsx          ← 全機能ツールバー（色・HL・リンク・動画等）
│       ├── BlockTagPanel.tsx    ← ブロック単位タグ付けパネル
│       └── BlockRenderer.tsx   ← 詳細ページ用レンダラー（KaTeX + コピーボタン）
│
├── lib/
│   ├── supabase.ts              ← ブラウザ・サーバー両用Supabaseクライアント
│   ├── types.ts                 ← Post / Profile / PostType 型定義
│   ├── utils.ts                 ← cn()
│   └── editor/
│       ├── extensions.ts        ← カスタム拡張（BlockId/Math/Callout/Video）
│       ├── SlashCommand.ts      ← /コマンドメニュー拡張
│       ├── useEditorConfig.ts   ← Tiptap設定フック（全拡張組み込み）
│       └── blockUtils.ts        ← extractText / extractBlockTags
│
├── supabase/
│   └── migrations/
│       ├── 001_init.sql         ← profiles/posts/likes + RLS + トリガー
│       └── 002_blocks.sql       ← blocks/blocks_text + post_block_tags + RPC
│
├── .env.example
├── .env.local                   ← Git管理外
├── next.config.ts
├── tsconfig.json
├── package.json
└── README.md
```

---

## 8. 画面設計

### 8.1 フィードページ（`/`）

**構成:**
- Hero タイトル（"KnOS EX"）
- FeedFilter（検索バー + タイプ選択 + 人気タグ）
- PostCard リスト

**PostCard 要素:**
- タイプバッジ（色分け）
- 投稿日時（相対表示: 「3分前」「2日前」等）
- 著者名（右端）
- タイトル（クリックで詳細へ）
- ソースURLドメイン（linkタイプ）
- コンテンツプレビュー（160文字、Markdown記号除去）
- タグチップ（最大5件、クリックでフィルター）
- いいねボタン + カウント

### 8.2 投稿作成（`/new`）

**構成:**
- タイプ選択ボタン群
- タイトル入力
- URL入力（linkタイプ時 or URLを入力した場合）
- **RichEditor**（ツールバー付きフルエディター）
- 投稿タグ入力（カンマ区切り）
- 表示名入力（省略可）
- 投稿ボタン

### 8.3 投稿詳細（`/post/[id]`）

**構成:**
- 戻るリンク
- タイプバッジ + 投稿日 + いいね数
- タイトル
- ソースURLリンク（linkタイプ）
- **BlockRenderer**（KaTeX + コードコピーボタン + 動画 + Callout等を完全レンダリング）
- タグチップ（クリックでフィード絞り込みへ）

### 8.4 NavBar

- ロゴ（`⬡ KnOS EX`）
- 投稿ボタン（PenLine アイコン）
- 未ログイン → Google / GitHub ログインボタン
- ログイン済み → メールアドレス + サインアウト

---

## 9. API・RPCインターフェース

すべて Supabase JS Client 経由。REST API は使用しない。

### 9.1 主要クエリ

```typescript
// フィード取得
supabase
  .from('posts')
  .select('*, profiles(display_name, avatar_url, is_anon)')
  .eq('is_published', true)
  .order('created_at', { ascending: false })
  .limit(30)

// キーワード検索
.or(`title.ilike.%${q}%,content.ilike.%${q}%,blocks_text.ilike.%${q}%`)

// タグフィルター
.contains('tags', [tag])

// いいね追加
supabase.from('likes').insert({ post_id, user_id })

// いいね削除
supabase.from('likes').delete().eq('post_id', id).eq('user_id', uid)

// ブロックタグ同期
supabase.rpc('sync_block_tags', { p_post_id: id, p_block_tags: entries })
```

### 9.2 認証

```typescript
// 匿名ログイン
supabase.auth.signInAnonymously()

// OAuth
supabase.auth.signInWithOAuth({
  provider: 'google' | 'github',
  options: { redirectTo: '/auth/callback' }
})

// OAuthコールバック
supabase.auth.exchangeCodeForSession(code)
```

---

## 10. セキュリティ（RLS）

### 10.1 ポリシー一覧

| テーブル | 操作 | 条件 |
|---------|------|------|
| `profiles` | SELECT | 全員 |
| `profiles` | UPDATE | `auth.uid() = id` |
| `posts` | SELECT | `is_published = TRUE` |
| `posts` | INSERT | `auth.uid() IS NOT NULL`（匿名含む） |
| `posts` | UPDATE | `auth.uid() = user_id` |
| `posts` | DELETE | `auth.uid() = user_id` |
| `likes` | SELECT | 全員 |
| `likes` | INSERT | `auth.uid() IS NOT NULL AND auth.uid() = user_id` |
| `likes` | DELETE | `auth.uid() = user_id` |
| `post_block_tags` | SELECT | 全員 |
| `post_block_tags` | INSERT/DELETE | 投稿の所有者のみ |

### 10.2 `sync_block_tags` 関数

`SECURITY DEFINER` で定義。内部で `auth.uid()` チェックは行わず、
呼び出し元の RLS で制御する（投稿所有者のみ呼び出せる）。

---

## 11. セットアップ手順

### 11.1 Supabase 設定

1. [supabase.com](https://supabase.com) で新規プロジェクト作成（無料）
2. SQL Editor で以下を順番に実行:
   - `supabase/migrations/001_init.sql`
   - `supabase/migrations/002_blocks.sql`
3. Settings → API から URL と anon key を取得

### 11.2 OAuth 設定（任意）

**Google:**
1. Google Cloud Console → OAuth 2.0 クライアント作成
2. リダイレクト URI: `https://xxxx.supabase.co/auth/v1/callback`
3. Supabase → Authentication → Providers → Google に設定

**GitHub:**
1. GitHub Settings → Developer settings → OAuth Apps → New
2. Authorization callback URL: `https://xxxx.supabase.co/auth/v1/callback`
3. Supabase → Authentication → Providers → GitHub に設定

### 11.3 ローカル起動

```bash
cp .env.example .env.local
# .env.local を編集して Supabase の値を入力

npm install
npm run dev
# → http://localhost:3000
```

### 11.4 Vercel デプロイ

```bash
npm i -g vercel
vercel

# Vercel Dashboard → Settings → Environment Variables に追加:
# NEXT_PUBLIC_SUPABASE_URL
# NEXT_PUBLIC_SUPABASE_ANON_KEY
# NEXT_PUBLIC_SITE_URL=https://your-app.vercel.app
```

**Supabase 側の追加設定:**
- Authentication → URL Configuration → Site URL に Vercel の URL を追加
- Redirect URLs にも `https://your-app.vercel.app/**` を追加

---

## 12. 開発フェーズ

### フェーズ EX-1（現在）— コア機能

- [x] DB スキーマ設計（posts / profiles / likes / post_block_tags）
- [x] RLS ポリシー
- [x] NavBar（認証UI）
- [x] フィードページ（SSR）
- [x] PostCard（いいね付き）
- [x] FeedFilter（検索・タイプ・タグ）
- [x] 投稿作成ページ（RichEditor統合）
- [x] 投稿詳細ページ
- [x] OAuth コールバック
- [x] RichEditor（Tiptap）
- [x] Toolbar（全書式 + 色 + HL + リンク + 画像 + 動画 + テーブル + Callout + 数式）
- [x] BlockTagPanel（ブロック単位タグ付け）
- [x] BlockRenderer（詳細ページ KaTeX + コピーボタン）
- [x] カスタム拡張（BlockId / MathInline / MathBlock / Callout / Video）
- [x] スラッシュコマンド（19種類）
- [x] globals.css（エディタースタイル完全版）

### フェーズ EX-2（次）

- [ ] 投稿詳細ページへの BlockRenderer 統合
- [ ] app/layout.tsx / app/page.tsx の再実装（全ページ揃える）
- [ ] 残りの missing ファイル補完（auth/callback, post/[id]）
- [ ] ブロックタグ検索（`?blocktag=xxx` クエリ対応）
- [ ] Supabase Storage 画像アップロード（ドラッグ&ドロップ）

### フェーズ EX-3（将来）

- [ ] コメント機能
- [ ] ユーザープロフィールページ（`/user/[id]`）
- [ ] 投稿編集
- [ ] KnOS Phase 1 との API 連携（`knos_entry_id` 活用）
- [ ] ブックマーク機能
- [ ] OGP / SNS シェア対応
- [ ] 無限スクロール（TanStack Query）
- [ ] 定義ブロックを利用してキーワード登場時定義ブロックへのハイパーリンク自動生成(カーソルを合わせて発動)
---

*本仕様書は KnOS EX v1.0 の実装根拠となる。*  
*本計画はKnOSと連続的なプロジェクトではあるが独立している。KnOS連携機能を実装する。*  