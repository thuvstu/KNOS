# KnOS Core — 個人知識OS

> **フェーズ 0〜5 + EX** 完全実装

---

## アーキテクチャ

```
knos-core/
├── backend/           FastAPI + SQLAlchemy (async)
│   ├── app/
│   │   ├── main.py          アプリエントリーポイント
│   │   ├── config.py        設定 (pydantic-settings)
│   │   ├── database.py      AsyncPG接続
│   │   ├── models/          SQLAlchemy ORM
│   │   ├── schemas/         Pydantic スキーマ
│   │   ├── routers/         FastAPI ルーター
│   │   │   ├── entries.py   エントリー CRUD
│   │   │   ├── search.py    ハイブリッド検索
│   │   │   ├── graph.py     接続グラフ
│   │   │   ├── import_.py   インポートパイプライン
│   │   │   ├── srs.py       SM-2 SRS
│   │   │   ├── taxonomy.py  タグ・トピック
│   │   │   └── ai.py        Gemini連携
│   │   ├── services/
│   │   │   ├── embedding.py      Embedding生成キュー
│   │   │   ├── search.py         RRF ハイブリッド検索
│   │   │   ├── srs.py            SM-2アルゴリズム
│   │   │   ├── connection.py     自動接続エンジン
│   │   │   └── import_pipeline/
│   │   │       ├── url_scraper.py      trafilatura
│   │   │       ├── file_importer.py    PDF/DOCX
│   │   │       └── adapters/
│   │   │           ├── notion.py       Notion API
│   │   │           ├── obsidian.py     Obsidian zip
│   │   │           ├── youtube.py      YouTube Data API
│   │   │           └── google_drive.py Drive API
│   │   └── middleware/
│   │       ├── auth.py        Cloudflare Access JWT
│   │       └── logging_.py    structlog
│   └── alembic/               DBマイグレーション
├── frontend/          Next.js 15 + React 19
│   ├── app/
│   │   ├── page.tsx          メイン (リスト + 詳細)
│   │   ├── graph/page.tsx    D3フォースグラフ
│   │   ├── srs/page.tsx      SM-2 フラッシュカード
│   │   ├── ai/page.tsx       Gemini Ask
│   │   ├── import/page.tsx   インポートUI
│   │   └── entries/[id]/     エントリー詳細
│   ├── components/
│   │   ├── Topbar.tsx        検索バー + ナビ
│   │   ├── Sidebar.tsx       タイプ / タグフィルター
│   │   ├── EntryCard.tsx     カードコンポーネント
│   │   ├── EntryDetail.tsx   詳細パネル
│   │   ├── QuickAdd.tsx      ⌘N クイック追加
│   │   └── ForceGraph.tsx    D3 v7 フォースグラフ
│   └── lib/
│       ├── api.ts            型付きAPIクライアント
│       ├── store.ts          Zustand グローバル状態
│       ├── utils.ts          ユーティリティ
│       └── hooks/            SWR フック
├── scripts/
│   └── init.sql              DB初期化 (extensions + tables)
├── docker-compose.yml        PostgreSQL 17 + PGroonga
└── Makefile
```

---

## 実装フェーズ

| フェーズ | 内容 | 実装 |
|---------|------|------|
| **0** | DB・スキーマ・Docker環境 | ✅ init.sql, docker-compose |
| **1** | エントリーCRUD・タグ・トピック | ✅ /entries, /tags, /topics |
| **2** | ハイブリッド検索 (PGroonga + pgvector RRF) | ✅ /search |
| **3** | Embedding生成キュー (Gemini) | ✅ services/embedding.py |
| **4** | 接続グラフ + 候補生成 | ✅ /graph, services/connection.py |
| **5** | SRS (SM-2) + AI Ask + インポートパイプライン | ✅ /srs, /ai, /import |
| **EX** | KnOS EX 公開プラットフォーム (別プロジェクト) | ✅ knos-ex/ |

---

## セットアップ

### 必要なもの

- Docker + Docker Compose
- Python 3.13+
- Node.js 22+
- [Gemini API Key](https://aistudio.google.com) (Embedding + LLM)

### 1. 環境変数

```bash
cp backend/.env.example backend/.env
# .env を編集して GEMINI_API_KEY, DB_PASSWORD 等を設定
```

### 2. DB起動

```bash
make up
# PostgreSQL 17 + PGroonga + pgvector + PostGIS が起動
```

### 3. バックエンド

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/api/docs
```

### 4. フロントエンド

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
# → http://localhost:3000
```

---

## API エンドポイント一覧

```
GET    /api/entries              エントリー一覧
POST   /api/entries              エントリー作成
GET    /api/entries/:id          エントリー詳細
PATCH  /api/entries/:id          エントリー更新
DELETE /api/entries/:id          エントリー削除 (soft)
POST   /api/entries/:id/restore  エントリー復元

GET    /api/search               ハイブリッド検索 (GET)
POST   /api/search               ハイブリッド検索 (POST)

GET    /api/graph/connections/:id  接続グラフ (depth=1-4)
POST   /api/graph/connections      接続作成
PATCH  /api/graph/connections/:id  接続更新
DELETE /api/graph/connections/:id  接続削除
GET    /api/graph/candidates       接続候補一覧
POST   /api/graph/candidates/:id   候補を承認/却下

POST   /api/import/url        URLスクレイプ
POST   /api/import/file       PDF/DOCX/TXT
POST   /api/import/obsidian   Obsidian zip
POST   /api/import/x-archive  Xアーカイブ JSON
POST   /api/import/youtube    YouTube高評価/プレイリスト

GET    /api/srs/queue         今日の復習キュー
GET    /api/srs/stats         SRS統計
POST   /api/srs/:id           SM-2レビュー記録
POST   /api/srs/:id/enroll    SRS登録

GET    /api/tags               タグ一覧
POST   /api/tags               タグ作成
GET    /api/topics             トピック一覧
POST   /api/topics             トピック作成

POST   /api/ai/ask             AI質問 (RAG)
POST   /api/ai/ask/stream      SSEストリーミング
POST   /api/ai/summarize/:id   エントリー要約
POST   /api/ai/suggest-connections/:id  接続候補提案

GET    /api/health             ヘルスチェック
```

---

## 検索モード

| モード | 説明 |
|--------|------|
| `hybrid` | PGroonga全文 + pgvector コサイン類似度 → **RRF** で統合 (デフォルト) |
| `fulltext` | PGroonga のみ (日本語形態素解析対応) |
| `semantic` | pgvector コサイン類似度のみ (Embedding必須) |

---

## Cloudflare Access (パーソナルクラウド保護)

```env
CF_TEAM_DOMAIN=your-team.cloudflareaccess.com
CF_AUD=your-audience-tag
```

設定すると全APIエンドポイントが `CF-Access-JWT-Assertion` ヘッダーで保護されます。
`DEBUG=true` の場合は認証スキップ。

---

## 自動接続エンジン

```env
AUTO_CONNECT_ENABLED=true
AUTO_CONNECT_THRESHOLD=0.82
```

新規エントリーのEmbedding生成後、コサイン類似度 > 閾値のペアを自動で `connection` テーブルに登録します。  
`false` の場合は `connection_candidate` テーブルに候補として保存し、UIから承認/却下できます。
