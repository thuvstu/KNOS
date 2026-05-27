# Personal Knowledge OS — 要件定義書

**バージョン:** 10.0  
**作成日:** 2026-05-10
**ステータス:** 確定版  
**対象:** Personal Knowledge OS 詳細設計書（v10）の根拠となる要件

---

## 目次

1. [機能要件](#1-機能要件)
2. [非機能要件](#2-非機能要件)
3. [外部インターフェース要件](#3-外部インターフェース要件)
4. [データ要件](#4-データ要件)
5. [セキュリティ要件](#5-セキュリティ要件)
6. [運用要件](#6-運用要件)
7. [制約事項](#7-制約事項)
8. [受け入れ基準](#8-受け入れ基準)

---

## 優先度の定義

| 優先度 | 説明 |
|--------|------|
| **Must** | 必須。この要件なしにシステムは成立しない |
| **Should** | 重要。フェーズ1〜2での実装を目指す |
| **Could** | 望ましい。フェーズ3〜4以降での実装を目指す |

---

## 1. 機能要件

### 1.1 エントリー管理

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-001 | エントリーの作成 | Must | ユーザーは任意の型（webpage, thought, book, video, document, media, person, org, place, event, definition, liked, ai_conv の13種）のエントリーを作成できる |
| FR-002 | エントリーの閲覧 | Must | 作成したエントリーの全フィールドを閲覧できる |
| FR-003 | エントリーの編集 | Must | 作成したエントリーのフィールドを部分的に更新できる |
| FR-004 | エントリーの論理削除 | Must | エントリーを削除しても物理削除はされず、`deleted_at` に日時が入るだけで復元可能 |
| FR-005 | エントリーの復元 | Must | 論理削除されたエントリーを元の状態に戻せる |
| FR-006 | お気に入り登録 | Should | エントリーを `is_favorite = TRUE` としてマークできる |
| FR-006b | ノイズ降格（Mute） | Should | エントリーを削除せず `is_muted = TRUE` にすることで検索ランキングから降格できる。一時メモ・スクラップURLが増えても「人生のゴミ箱」化しない仕組み |
| FR-006c | アクセス記録 | Must | エントリー閲覧時に `accessed_at` を自動更新する。将来の時系列機能・再浮上の基盤 |
| FR-007 | 型別拡張フィールド | Must | エントリー型に応じた専用フィールド（書籍ならISBN/読書状態、動画なら字幕等）を Class Table Inheritance パターン（`entry` + `entry_xxx` 拡張テーブル）で保持できる |

### 1.2 検索

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-101 | 全文検索 | Must | pgroonga による日本語対応全文検索ができる |
| FR-102 | セマンティック検索 | Must | `gemini-embedding-2-preview`（3072次元）を使った意味ベースの類似度検索ができる |
| FR-103 | ハイブリッド検索 | Must | 全文検索とセマンティック検索を RRF で統合したモードをデフォルトとする |
| FR-104 | 型フィルタ | Must | 特定の型（webpage, thought 等）に絞って検索できる |
| FR-105 | タグフィルタ | Must | 特定のタグが付いたエントリーに絞って検索できる |
| FR-106 | トピックフィルタ | Should | 特定のトピックに属するエントリーに絞って検索できる |
| FR-107 | 日付範囲フィルタ | Should | 作成日の範囲を指定して検索できる |
| FR-108 | ソート | Must | 関連度・作成日・更新日で結果を並べ替えられる |
| FR-109 | 検索サジェスト | Should | タイトル・タグのオートコンプリートが動作する |

### 1.3 知識接続

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-201 | 接続候補生成 | Should | 新規エントリー作成時に類似度が閾値を超える既存エントリーを `connection_candidate`（候補）として生成する。**自動で確定接続は作らない。** ユーザーが候補を確認・承認した時点で正式な `connection` になる |
| FR-201b | 候補の承認・却下 | Should | `connection_candidate` をUIで一覧表示し、承認（→ `connection` 作成）または却下できる |
| FR-202 | 手動接続 | Must | ユーザーが任意の2エントリー間に関係を定義できる |
| FR-203 | 関係型の指定 | Must | 接続に型（related/references/contradicts/extends/exemplifies/authored_by/published_by/located_at/occurred_at）を付与できる |
| FR-204 | Knowledge Graph 可視化 | Should | エントリー間の接続を `@xyflow/react` でインタラクティブに可視化できる（フェーズ4実装。フェーズ3はBacklinks・Related listのみ） |
| FR-205 | グラフ深さ指定 | Should | グラフの展開深さを1〜4段階で指定できる |
| FR-206 | 接続強度の設定 | Should | 手動接続の強度を0〜1で指定できる |
| FR-207 | 接続の編集・削除 | Must | 既存の接続を編集・削除できる |

### 1.4 タグ・トピック管理

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-301 | タグの作成・削除 | Must | タグを作成・削除できる |
| FR-302 | エントリーへのタグ付け | Must | エントリーに複数のタグを付与・削除できる |
| FR-303 | トピックの階層管理 | Should | トピックを階層構造（親子関係）で管理できる |
| FR-304 | エントリーへのトピック割当 | Should | エントリーをトピックに紐付けられる |

### 1.5 SRS（間隔反復復習）

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-401 | SM-2アルゴリズム | Should | 復習結果（グレード0〜5）から SuperMemo Algorithm SM-2 (1987) に基づいて次回復習日を計算する。**SRSはPKMと独立したUX要求（毎日レビュー・摩擦ゼロ・習慣化）を持つ独立アプリ級機能。フェーズ3以降で実装する。** |
| FR-402 | 本日の復習キュー | Should | `srs_current` ビュー経由で本日復習すべきエントリーの一覧を取得できる |
| FR-403 | 復習結果の記録 | Should | 0〜5のグレードで復習結果を記録し、`srs_review` テーブルに蓄積する |
| FR-404 | 復習統計 | Should | 復習の統計（日別・レベル別）を表示できる |

### 1.6 インポート

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-501 | URL取り込み | Must | WebページのURLを入力して内容をスクレイプし、`entry_webpage` として保存できる |
| FR-502 | スクレイプフォールバック（curl_cffi） | Should | httpx+trafilatura で失敗した場合に curl_cffi（TLS偽装）でリトライできる。**実際の80%はtrafilaturaで十分。** |
| FR-502b | スクレイプフォールバック（Playwright） | Could | curl_cffi でも失敗した場合に playwright（ヘッドレスChromium）でリトライできる。Chromium依存・WSL2メモリ消費・メンテコストが高いため後回しでよい |
| FR-503 | PDFインポート | Should | PDFファイルをアップロードして pdfplumber でテキスト抽出し、`entry_document` 化できる |
| FR-504 | オフィス文書インポート | Should | DOCX/XLSX/PPTX ファイルをインポートできる |
| FR-505 | Notionインポート | Could | Notion API（v2023-06-01）経由でページを取り込める |
| FR-506 | Google Driveインポート | Could | Google Drive API v3 でファイルのテキストをエクスポートして取り込める（ローカル保存なし） |
| FR-507 | Obsidianインポート | Could | Obsidianエクスポート（Markdown zip）をインポートし、`[[wiki-link]]` を KnOS 接続（references）に変換できる |
| FR-508 | Xアーカイブインポート | Could | X（Twitter）アーカイブJSONをインポートして `entry_liked` として保存できる |
| FR-509 | YouTube Likedインポート | Could | YouTube Data API v3 で高評価動画一覧をインポートできる（`YOUTUBE_API_KEY` 設定時のみ有効） |

### 1.7 共有・入力

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-601 | Android Share Target | Must | Android の共有メニューから URL/テキストを KnOS に送信できる（Next.js route handler で処理）。**capture frictionを最も下げる最重要機能**。PWA share_target・Android Chrome挙動差・オフライン処理・認証の組み合わせで実装が泥臭いため、フェーズ2で重点実装する |
| FR-602 | クイック追加 | Must | 全画面から1タップでエントリーを追加できるフローティングUI |
| FR-603 | URL直接入力 | Must | URLを入力して即座に取り込み開始できる |
| FR-604 | テキスト直接入力 | Must | テキストを入力して即座に `thought` エントリーとして保存できる |

### 1.8 その他

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-701 | AI会話ログ保存 | Should | AIチャットの会話ログを `entry_ai_conv` として保存できる |
| FR-702 | 場所の地図表示 | Could | `entry_place` の PostGIS 位置情報を地図上に表示できる |
| FR-703 | Markdownレンダリング | Must | エントリーの `content` フィールドを Markdown としてレンダリングできる |

---

## 2. 非機能要件

### 2.1 パフォーマンス

| ID | 要件 | 目標値 | 測定方法 |
|----|------|--------|---------|
| NFR-001 | 検索応答時間 | < 500ms（10万件未満） | APIレスポンスの `timing_ms.total` で計測 |
| NFR-002 | Embedding生成時間 | < 2秒 | Gemini API通信含む実測 |
| NFR-003 | ページ初期表示 | < 2秒 | Lighthouse TTI（Time to Interactive） |
| NFR-004 | PDFインポート（50ページ） | < 30秒 | 実測 |
| NFR-005 | Knowledge Graph（100ノード） | < 1秒 | React Flow レンダリング完了まで |
| NFR-006 | 想定同時リクエスト数 | 1ユーザー・通常10 req/分以下 | 個人利用を前提 |

### 2.2 可用性

| ID | 要件 | 目標値 | 説明 |
|----|------|--------|------|
| NFR-101 | システム稼働時間 | 24/7（WSL2起動時） | PC 停止中はアクセス不可（許容） |
| NFR-102 | データ損失耐性 | 日次バックアップ以降のデータは復旧可能 | 3層バックアップにより通常障害からの復旧が可能。WSL2+個人PC環境で「ゼロ損失」は保証不能のため、「日次バックアップ時点まで復元可能」を現実的な目標とする |
| NFR-103 | 障害復旧時間 | < 1時間 | Docker・systemd 再起動で復旧 |
| NFR-104 | バックアップ頻度 | 毎日 | cron で PostgreSQL ダンプを GitHub にプッシュ |

### 2.3 保守性

| ID | 要件 | 目標値 | 説明 |
|----|------|--------|------|
| NFR-201 | ファイル行数制限 | 1000行以下/ファイル | 原則として1ファイル1000行を超えない |
| NFR-202 | レイヤー分離 | 機能単位 | Brain / Data / Interface Layer の分離を維持 |
| NFR-203 | 外部API分離 | Adapter パターン | 外部サービス依存はすべて `adapters/` に隔離 |
| NFR-204 | データ独立性 | 完全 | UI が消えてもデータは無傷で存在する |
| NFR-205 | 一人運用設計 | 必須 | 全ての運用タスクを一人で完結できる |

### 2.4 永続性

| ID | 要件 | 目標値 | 説明 |
|----|------|--------|------|
| NFR-301 | データフォーマット | オープン標準 | PostgreSQL + JSON + Markdown + SQLite |
| NFR-302 | 長期アクセス保証 | 30年 | どのシステムからも読み出せる形式を維持 |
| NFR-303 | 可搬バックアップ | SQLite | PostgreSQL が使えなくなった場合の代替読み出し手段 |
| NFR-304 | データ所有権 | 完全自己所有 | データは常にユーザーのローカル環境にのみ存在する |

### 2.5 ユーザビリティ

| ID | 要件 | 目標値 | 説明 |
|----|------|--------|------|
| NFR-401 | 入力摩擦 | 最小 | クイック追加は2タップ以内で開始。**知識OSの最大の敵は「記録の面倒さ」**。Ctrl+V貼り付け・Android共有・5秒以内capture・後整理前提・未分類許容の設計を維持する |
| NFR-405 | 後整理前提 | 必須 | タグ・トピック・接続は記録時に強制しない。未整理エントリーが大量に存在しても検索・閲覧できること |
| NFR-402 | モバイル対応 | Android Chrome 完全動作 | PWA としてインストール可能、主要機能すべてが使える |
| NFR-403 | ダークモード | 対応 | システム設定に従い自動切替 |
| NFR-404 | 視覚的型識別 | カラー+アイコン | 全エントリー型に固有の色とアイコンを割り当て |

---

## 3. 外部インターフェース要件

| ID | 要件 | 必須/任意 | 説明 |
|----|------|----------|------|
| EIR-001 | Gemini Embedding API | 必須 | `gemini-embedding-2-preview` モデルによる 3072 次元ベクトル生成（MRL対応）。Google AI Studio APIキーで無料利用可 |
| EIR-001b | Gemini LLM API | 必須 | `gemini-2.5-flash`（主）・`gemini-3-flash-preview`（副）。サマリー生成・構造化抽出・OCR用。無料枠あり |
| EIR-001c | ollama / llama.cpp | 任意 | ローカルLLM（`qwen2.5:7b` 等）。API コストゼロ・完全オフライン動作。Gemini の代替として使用可 |
| EIR-002 | Cloudflare Access JWT | 必須 | リクエストヘッダ `Cf-Access-Jwt-Assertion` の検証（1時間 TTL キャッシュ） |
| EIR-003 | Cloudflare Tunnel | 必須 | 外部公開用のリバーストンネル（クレジットカード不要） |
| EIR-004 | Notion API | 任意 | ページ取り込み用（v2023-06-01）。フェーズ4 |
| EIR-005 | Google Drive API | 任意 | ファイルテキスト抽出用（v3）。フェーズ4 |
| EIR-006 | YouTube Data API v3 | 任意 | Liked動画取得用。`YOUTUBE_API_KEY` 未設定時は 503 を返す。フェーズ4 |
| EIR-007 | Gemini Vision API | 任意 | 画像 OCR 用。フェーズ2以降 |

---

## 4. データ要件

| ID | 要件 | 説明 |
|----|------|------|
| DR-001 | エントリー型 | webpage, thought, book, video, document, media, person, org, place, event, definition, liked, ai_conv の 13 種をサポート |
| DR-002 | 文字セット | UTF-8 |
| DR-003 | 言語対応 | 日本語・英語・中国語繁体字（BCP 47 タグ `lang CHAR(10)` で管理） |
| DR-004 | 論理削除 | 全エントリーは `deleted_at TIMESTAMPTZ` による論理削除。物理削除はしない |
| DR-005 | データ保持期間 | 無期限（ユーザーが明示的に削除するまで） |
| DR-006 | ファイル保存 | `~/knowledge-os/blobs/` にローカル保存。DB にはパスのみ格納 |
| DR-007 | Embedding 次元数 | プロバイダー依存（`EMBEDDING_DIMENSION` 環境変数で管理）。現在: gemini-embedding-2-preview = デフォルト3072、推奨768（MRL截断）。プロバイダー変更時はDBマイグレーションが必要 |
| DR-008 | 接続型定義 | `connection_type_def` テーブルで管理。新型追加は INSERT 1行 + インデックス再作成 |
| DR-009 | SRS 状態 | `srs_review` の最新レコードから `srs_current` ビューで導出。`entry_definition` に状態を持たない |
| DR-010 | metadata JSONB | 型別拡張テーブルにカラムを追加するほどではないソース固有情報を格納。検索の主軸には使用しない |
| DR-011 | SQLite export仕様 | PostgreSQL固有型（vector・jsonb・timestamptz・array・geometry）は `serialize_value()` で安全に変換。`_schema_meta` テーブルにカラムのPG型情報を保持し、`_export_info` にスキーマバージョンを記録する。vectorデータはexport対象外（input_textから再生成可能） |

---

## 5. セキュリティ要件

| ID | 要件 | 説明 |
|----|------|------|
| SEC-001 | 認証 | Google OAuth（Cloudflare Access 経由）。自分のメールアドレスのみ許可 |
| SEC-002 | アクセス制御 | 登録された1つのメールアドレスのみアクセス可能 |
| SEC-003 | 通信暗号化 | HTTPS（Cloudflare Tunnel で TLS 終端） |
| SEC-004 | API 保護 | 全エンドポイントで JWT 検証を必須化。公開鍵は TTL 1時間でキャッシュ |
| SEC-005 | シークレット管理 | `.env` ファイルで管理。`.gitignore` に追加必須。Git 管理外 |
| SEC-008 | バックアップ暗号化 | PostgreSQL dump を GitHub へ push する前に **age** で暗号化必須。秘密鍵（`backup-key.txt`）はGit管理外。人生ログ（思考・AI会話・URL履歴）が平文でクラウドに存在しないこと |
| SEC-006 | ローカルバインディング | バックエンドは `127.0.0.1` にのみバインド |
| SEC-007 | 開発環境分離 | `DEBUG=true` 時に認証スキップ可能（localhost 開発専用） |

---

## 6. 運用要件

| ID | 要件 | 説明 |
|----|------|------|
| OPR-001 | WSL2 自動起動 | Windows ログオン時に WSL2 + Docker + systemd サービスが自動起動する |
| OPR-002 | systemd 管理 | FastAPI・Next.js を systemd サービス（`Restart=on-failure`）として管理 |
| OPR-003 | Docker 管理 | PostgreSQL を Docker Compose で管理（`restart: unless-stopped`） |
| OPR-004 | 日次バックアップ | cron で毎日 3:00 に PostgreSQL ダンプ → **age暗号化** → GitHub private リポジトリにプッシュ（SEC-008準拠） |
| OPR-005 | 週次可搬バックアップ | SQLite エクスポートを外付けドライブに保存（推奨） |
| OPR-006 | ログ管理 | systemd journal で一元管理。`journalctl -u knos-backend -f` でリアルタイム確認 |
| OPR-007 | 監視 | 手動確認。`curl /health`、`journalctl`、`pg_stat_statements` で問題を把握 |
| OPR-008 | キュー消失の許容（フェーズ1） | WSL2 再起動時はインメモリ Embedding キューが消えることを許容。フェーズ2で DB バックアップ化する |
| OPR-009 | Embedding ジョブ回復（フェーズ2以降） | 再起動後に `recover_embedding_jobs()` が自動実行され、`status IN ('queued', 'running')` のジョブをキューに再投入する（lifespan 登録） |

---

## 7. 制約事項

| ID | 制約 | 説明 |
|----|------|------|
| CON-001 | 予算ゼロ | 有料サービス・クレジットカード登録不可 |
| CON-002 | 単一ユーザー | マルチユーザー機能はスコープ外 |
| CON-003 | 実行環境 | Windows 11 + WSL2 (Ubuntu 24.04 LTS)。Python 3.13、Node.js 22 LTS、PostgreSQL 17 |
| CON-004 | クライアント | PC ブラウザ + Android Chrome（PWA） |
| CON-005 | 外部依存 | Gemini API（Embedding: gemini-embedding-2-preview、LLM: gemini-2.5-flash）。ローカルLLMとして ollama も利用可。Cloudflare Tunnel（PC 起動中のみ） |
| CON-006 | ネットワーク | 外部アクセスには Cloudflare Tunnel が稼働していること |
| CON-007 | データ量 | 個人利用想定（年間数千〜数万エントリー） |
| CON-008 | 同時利用 | 単一ユーザーの逐次操作のみ。競合解決は不要 |

---

## 8. 受け入れ基準

フェーズごとに「これが全て ✅ になれば次のフェーズに進める」の基準を定義する。

### 8.0 フェーズ0 受け入れ基準

| ID | 基準 | 検証方法 |
|----|------|---------|
| AC-001 | テキストメモをエントリーとして保存できる | curl or HTMLフォームでテスト |
| AC-002 | 保存したエントリーをキーワード検索で見つけられる | `GET /entries?q=キーワード` |
| AC-003 | **3日連続で何かを記録した** | 実際の使用記録で確認 |

### 8.1 フェーズ1 受け入れ基準

| ID | 基準 | 検証方法 |
|----|------|---------|
| AC-101 | WebページのURLを入力してエントリーとして保存できる | 実際の URL でテスト |
| AC-102 | フェーズ0のSQLiteデータがPostgreSQLに移行済み | エントリー数・タグの一致確認 |
| AC-103 | 保存したエントリーを Hybrid Search で見つけられる | キーワード + 類似意味で検索 |
| AC-104 | エントリーの一覧・詳細・編集・論理削除・復元ができる | CRUD 全操作テスト |
| AC-105 | Embedding が自動生成される（非同期キュー経由） | `embedding` テーブルのレコード確認 |
| AC-106 | 日次バックアップがage暗号化されGitHubにプッシュされている | 翌日に確認・復元テスト実施 |

### 8.2 フェーズ2 受け入れ基準

| ID | 基準 | 検証方法 |
|----|------|---------|
| AC-201 | Android Chrome からアクセスし PWA としてインストールできる | 実機テスト |
| AC-202 | Android 共有メニューから KnOS に取り込める | 実機テスト |
| AC-203 | Cloudflare Access 認証が機能している | 未認証ブラウザで 401 確認 |
| AC-204 | 全 13 型のエントリーが作成できる | 型別テスト |
| AC-205 | PDF/DOCX ファイルをインポートできる | 実ファイルでテスト |
| AC-206 | httpx+trafilatura・curl_cffiのフォールバックが動作する（Playwrightは任意） | Bot 検知サイトでテスト |
| AC-207 | `recover_embedding_jobs()` が再起動後に正しく動作する | 意図的な強制終了後に確認 |

### 8.3 フェーズ3 受け入れ基準

| ID | 基準 | 検証方法 |
|----|------|---------|
| AC-301 | Related entries list・Backlinks が表示される | エントリー詳細画面で確認 |
| AC-302 | 手動で2エントリー間に接続を作成できる | 接続作成UIテスト |
| AC-303 | SRS 復習キューが表示され結果を記録できる | 定義カードの復習テスト |
| AC-304 | ダークモードが正しく切り替わる | システム設定変更で確認 |
| AC-305 | 自動Connection有効化後にGraph毛玉化が発生していない | 50件以上登録後にConnection数確認 |

### 8.4 フェーズ4 受け入れ基準

| ID | 基準 | 検証方法 |
|----|------|---------|
| AC-401 | Knowledge Graph が `@xyflow/react` で可視化される | Graph 画面の目視確認 |
| AC-402 | Notion ページを取り込める | 実 Notion ページでテスト |
| AC-403 | Google Drive ファイルを取り込める（ローカル保存なし） | 実 GDrive ファイルでテスト |
| AC-404 | Obsidian エクスポートをインポートし wiki-link が接続に変換される | 実エクスポートでテスト |
| AC-405 | X アーカイブ JSON をインポートできる | 実アーカイブでテスト |

---

*本要件定義書は Personal Knowledge OS の全要件を定義する。*  
*詳細設計書（v10）と併せて読み、要件の充足を確認すること。*  
*優先度: Must > Should > Could の3段階。*
