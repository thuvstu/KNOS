# Personal Knowledge OS — 詳細設計書

**バージョン:** 10.0  
**作成日:** 2026-05-10  
**ステータス:** 確定版（初期実装用）

---

## 目次

1. [プロジェクト概要](#1-プロジェクト概要)
2. [設計哲学と制約](#2-設計哲学と制約)
3. [システム全体構成](#3-システム全体構成)
4. [インフラ・環境仕様](#4-インフラ環境仕様)
5. [データモデル仕様](#5-データモデル仕様)
6. [ストレージ戦略](#6-ストレージ戦略)
7. [Brain Layer仕様](#7-brain-layer仕様)
8. [API仕様](#8-api仕様)
9. [フロントエンド・UI仕様](#9-フロントエンドui仕様)
10. [外部連携・インポート仕様](#10-外部連携インポート仕様)
11. [衛星システム仕様](#11-衛星システム仕様)
12. [開発フェーズ計画](#12-開発フェーズ計画)
13. [非機能要件](#13-非機能要件)
14. [ロギング・モニタリング仕様](#14-ロギングモニタリング仕様)

---

## 1. プロジェクト概要

### 1.1 プロジェクト名

**Personal Knowledge OS**（以下 "KnOS"）

### 1.2 一文定義

生涯にわたって学んだこと・考えたこと・出会った情報のすべてを一箇所に記録し、時間を超えた知識の接続と発見を可能にする、個人用の知識管理基盤。

### 1.3 解決する問題

- 情報が15以上のツールにサイロ化しており横断検索・接続ができない
- 3年前に読んだ記事と今日の思考がつながっていない
- 過去に作った4つのシステムは「入力の重さ・複雑化・UIとデータの密結合」により廃止
- 「一生使う」要件に対してデータの永続性が担保されていなかった

### 1.4 コア要件（優先順）

| 優先度 | 要件 | 説明 |
|--------|------|------|
| 1 | Input-Easy | 入力摩擦を最小化。続かないシステムは死ぬ |
| 2 | Data-Permanent | データがツールより長生きすること |
| 3 | Search-Advanced | セマンティック検索・多様なクエリ・ソート |
| 4 | Connection-Clear | 知識間の関係を可視化・発見できること |

### 1.5 スコープ外（このシステムが担わないもの）

- テスト結果管理（別プロジェクト `knowledge-os-test` として独立実装）
- ナビゲーション/経路案内（OSM/OTP/GTFS-JP — 別プロジェクト `knowledge-os-navi` として独立）
- チームコラボレーション機能
- 課金・サブスクリプション管理

---

## 2. 設計哲学と制約

### 2.1 設計原則

**原則1: データが先、UIは後**  
データは特定のUIに依存してはならない。UIが壊れても・作り直しても、データは無傷で存在し続ける。データフォーマットはオープン標準を選ぶ。

**原則2: 自作するのはBrain Layerだけ**  
DB・HTTP・認証・ファイル管理には既存の成熟したツールを使う。Embedding・セマンティック検索・Knowledge Graphは自分の知識に最適化された唯一の層なので自作する。

**原則3: 入力は既存の最高のツールを使い倒す**  
入力に摩擦が生まれた瞬間にシステムは死ぬ。Capture層は最小限の自作で済ませ、Web Clipper・API・ファイルインポートに集中する。

**原則4: 統合は段階的に**  
N個のサービスを一度に統合するとN²の障害点が生まれる。フェーズを分けて確実に動くものから積み上げる。

**原則5: UIは使いやすさとわかりやすさを最優先**  
機能面では入力・検索・閲覧の摩擦をゼロに近づける。デザイン面では情報の構造が一目でわかるレイアウトを維持する。見た目のための複雑さは排除する。

**原則6: Friction削減は機能追加より優先する**  
知識OSの最大の敵は「記録の面倒さ」であり、アルゴリズムの洗練度ではない。Ctrl+V貼り付け・Android共有・5秒以内capture・後整理前提・未分類許容を設計の核に置く。タグ・トピック・接続は記録時に強制しない。整理は後でよい。

### 2.2 ハードな制約

- **予算:** 無料のみ。有料サービス・クレジットカード登録不可
- **デバイス:** PC（Windows/WSL2）+ Android
- **永続性:** 10年・30年後も同じデータにアクセスできること
- **メンテナンス:** 一人で管理できる複雑度に抑える

### 2.3 過去の失敗から学んだ禁止事項

- UIとデータを同じレポジトリ・モジュールに密結合させない
- 「全部統合してから使う」設計にしない（フェーズ1で動くものを作る）
- 1000行を超えるファイルを作らない（分割を徹底する）
- 外部APIへの依存はAdapterパターンで隔離する

---

## 3. システム全体構成

### 3.1 アーキテクチャ全体図

```
┌─────────────────────────────────────────────────────────┐
│                   Interface Layer                        │
│  PWA (Next.js)  ·  Android PWA  ·  CLI  ·  Bookmarklet  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS
┌────────────────────────▼────────────────────────────────┐
│              Cloudflare Tunnel + Access                  │
│         （Google OAuth認証 · 外部公開ゲートウェイ）          │
└────────────────────────┬────────────────────────────────┘
                         │ localhost
┌────────────────────────▼────────────────────────────────┐
│                Brain Layer (WSL2)                        │
│  FastAPI  ·  Embedding Engine  ·  Search Engine          │
│  Connection Engine  ·  Import Pipeline  ·  Task Queue   │
└──────────┬─────────────────────────────┬────────────────┘
           │                             │
┌──────────▼──────────┐   ┌─────────────▼──────────────────┐
│   Data Layer        │   │   Storage Layer                 │
│  PostgreSQL 16      │   │  ~/knowledge-os/blobs/          │
│  + pgvector         │   │  （PDF · 動画 · 画像 · Office）   │
│  + pgroonga         │   │  GitHub (code + DB backup)      │
│  + PostGIS          │   │  SQLite (可搬バックアップ)        │
└─────────────────────┘   └─────────────────────────────────┘
```

### 3.2 衛星システム（別リポジトリ）

```
knowledge-os/          ← メインリポジトリ（本設計書の対象）
knowledge-os-navi/     ← Navi PWA (OSM/OTP/GTFS)
knowledge-os-test/     ← Test Result System (GAS + Classroom API)
knowledge-os-quiz/     ← Quiz/Learning App (Next.js or GAS)
```

衛星システムはKnOS CoreのAPIを呼び出すことができる。逆方向の依存は禁止。

---

## 4. インフラ・環境仕様

### 4.1 開発・本番環境

| 項目 | 値 |
|------|-----|
| ホストOS | Windows 11 |
| 実行環境 | WSL2 (Ubuntu 24.04 LTS)、**networkingMode=mirrored**（同WiFi内Android直接アクセス対応） |
| Pythonバージョン | 3.13以上（最新安定版: 3.13.13） |
| Node.jsバージョン | 22 LTS（Node.js 20はMaintenance終了→非推奨） |
| PostgreSQLバージョン | 17以上（最新: 17.9） |
| pgvectorバージョン | 0.8.2以上（⚠️ CVE-2026-3172修正を含む必須セキュリティアップデート） |
| pgroognaバージョン | 4.x以上（最新: 4.0.6、2026-04-07リリース） |
| PostGISバージョン | 3.x |

**⚠️ WSL2の長期運用リスクと移行パス**

WSL2は開発環境として優秀だが、「24/7常駐・長期運用」には以下の問題がある。

| リスク | 説明 |
|--------|------|
| Windows Update | 再起動でWSL2・Docker・systemdが停止する |
| スリープ復帰 | ネットワーク切断・Docker再起動が必要になることがある |
| ファイルI/O | `/mnt/c/` 経由のアクセスは3〜5倍遅い |
| systemd安定性 | WSL2のsystemdはネイティブLinuxより不安定なケースがある |

**長期的な移行先（推奨）:** フェーズ3以降でmini PCやLinuxネイティブへの移行を検討する。

```
現在: Windows 11 + WSL2（開発・初期運用）
    ↓ フェーズ3〜4以降
理想: mini PC（中古で十分）+ Ubuntu 24.04 LTS ネイティブ
      または Proxmox + Debian VM（仮想化で可搬性確保）
```

データはPostgreSQL dump + blobs で完全移行可能。WSL2→Linuxネイティブへの移行コストはほぼゼロ。

### 4.2 ディレクトリ構成

```
~/knowledge-os/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py               ← 設定・環境変数の一元管理
│   │   ├── database.py             ← DB接続・セッション管理
│   │   ├── models/                 ← SQLAlchemy モデル
│   │   │   ├── entry.py
│   │   │   ├── extensions/         ← 型別拡張モデル
│   │   │   ├── brain.py            ← embedding, connection
│   │   │   └── taxonomy.py         ← tag, topic
│   │   ├── schemas/                ← Pydantic スキーマ（型別）
│   │   ├── routers/                ← APIルーター
│   │   │   ├── entries.py
│   │   │   ├── search.py
│   │   │   ├── graph.py
│   │   │   ├── import_.py
│   │   │   ├── taxonomy.py
│   │   │   └── srs.py
│   │   ├── services/
│   │   │   ├── embedding.py        ← Embedding生成・管理
│   │   │   ├── search.py           ← Hybrid Search
│   │   │   ├── connection.py       ← Connection Engine
│   │   │   ├── srs.py              ← SM-2アルゴリズム
│   │   │   ├── task_queue.py       ← 非同期タスクキュー
│   │   │   └── import_pipeline/
│   │   │       ├── base.py         ← 共通パイプライン
│   │   │       ├── url_scraper.py
│   │   │       ├── file_importer.py
│   │   │       └── adapters/       ← 外部サービスアダプター
│   │   │           ├── notion.py
│   │   │           ├── google_drive.py
│   │   │           ├── youtube.py
│   │   │           ├── x_archive.py
│   │   │           └── obsidian.py
│   │   ├── middleware/
│   │   │   ├── auth.py             ← Cloudflare Accessトークン検証
│   │   │   └── logging_.py         ← リクエストロギング
│   │   └── errors.py               ← エラークラス・ハンドラ定義
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_entries.py
│   │   ├── test_search.py
│   │   └── test_import.py
│   ├── pyproject.toml
│   └── .env                        ← Git管理外
├── frontend/
│   ├── app/                        ← Next.js App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx                ← ダッシュボード
│   │   ├── search/page.tsx
│   │   ├── entries/[id]/page.tsx
│   │   ├── graph/page.tsx
│   │   └── api/share/route.ts      ← Android Share Target受け口
│   ├── components/
│   ├── lib/
│   │   ├── api.ts                  ← API クライアント
│   │   └── hooks/
│   ├── public/
│   │   └── manifest.json           ← PWA マニフェスト
│   └── package.json
├── blobs/                          ← 実ファイル（Git管理外）
│   ├── documents/
│   │   └── YYYY/
│   ├── media/
│   │   ├── images/
│   │   └── audio/
│   └── tmp/
├── scripts/
│   ├── backup.sh                   ← PGダンプ+GitPush
│   ├── export_sqlite.py            ← PostgreSQL→SQLite変換
│   └── setup.sh                    ← 初回セットアップ
├── docker-compose.yml
└── README.md
```

### 4.3 Dockerセットアップ（PostgreSQL + 拡張）

pgroonga公式Dockerイメージ `groonga/pgroonga` を使用する。カスタムaptビルド不要・PG17対応・pgroonga 4.x（最新4.0.6）が同梱済み。

```yaml
# docker-compose.yml
version: '3.9'
services:
  db:
    build:
      context: .
      dockerfile: Dockerfile.db
    container_name: knos_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: knos
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: knos
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U knos"]
      interval: 10s
      timeout: 5s
      retries: 5
```

```dockerfile
# Dockerfile.db
# pgroonga 4.x（最新4.0.6）+ PostgreSQL 17 の公式イメージをベース
# カスタムaptビルド不要。groonga/pgroongaイメージはpgroongaを同梱済み。
FROM groonga/pgroonga:latest-debian-17

# pgvector 0.8.2以上（CVE-2026-3172修正済み・必須）
RUN apt-get update && apt-get install -y postgresql-17-pgvector

# PostGIS
RUN apt-get install -y postgresql-17-postgis-3

CMD ["postgres"]
```

```sql
-- scripts/init.sql（DBの初期化）
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgroonga;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### 4.4 WSL2 プロセス管理・自動起動

WSL2はWindowsの再起動で停止する。以下の構成で自動起動と常駐を実現する。

#### 4.4.1 systemd サービス定義

WSL2のsystemdを有効にする（`/etc/wsl.conf` に `[boot] systemd=true` を設定）。

```ini
# /etc/systemd/system/knos-backend.service
# 注意: %i はテンプレートユニット専用の展開子。通常の .service ファイルでは
# ユーザー名を直接指定すること（%i は空文字に展開されサービスが起動しない）。
[Unit]
Description=KnOS Backend (FastAPI)
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/knowledge-os/backend
EnvironmentFile=/home/YOUR_USERNAME/knowledge-os/backend/.env
ExecStart=/home/YOUR_USERNAME/knowledge-os/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/knos-frontend.service
[Unit]
Description=KnOS Frontend (Next.js)
After=network.target knos-backend.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/knowledge-os/frontend
ExecStart=/usr/bin/node .next/standalone/server.js
Environment=PORT=3000
Environment=HOSTNAME=127.0.0.1
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 4.4.2 Windows起動時のWSL自動起動

Windows Task Schedulerにトリガー「ログオン時」で以下を登録する。

```batch
wsl -d Ubuntu -e bash -c "sudo systemctl start docker knos-backend knos-frontend"
```

#### 4.4.3 サービス管理コマンド

```bash
# 起動 / 停止 / 再起動
sudo systemctl start knos-backend knos-frontend
sudo systemctl stop knos-backend
sudo systemctl restart knos-backend

# 状態確認
sudo systemctl status knos-backend

# ログ確認（リアルタイム）
journalctl -u knos-backend -f

# 自動起動の有効化
sudo systemctl enable knos-backend knos-frontend
```

#### 4.4.4 ヘルスチェックと再起動ポリシー

- `Restart=on-failure` : プロセスがゼロ以外の終了コードで停止した場合に自動再起動
- `RestartSec=5s` : 連続クラッシュ時のスロットリング
- Cloudflare TunnelもDockerコンテナとして `restart: unless-stopped` で管理

### 4.5 外部公開構成（Cloudflare Tunnel + Access）

**⚡ Mirrored Networking Mode 有効化により、アクセス戦略が2層になった**

```
【家のWiFi内】Android / PC
    → Windows の LAN IP（例: 192.168.1.x）で WSL2 に直接アクセス
    → Cloudflare Tunnel 不要
    → レイテンシ最小・完全オフライン動作可

【外出先】Android
    → Cloudflare Tunnel 経由でアクセス
    → PC（WSL2）が起動している必要あり
```

**セキュリティ注意:** Mirrored modeでは WSL2 サービスがLAN全体から見える。  
FastAPI は必ず `127.0.0.1` バインドのまま維持し、**LAN公開用には別途 `0.0.0.0` バインドを使う場合はWindowsファイアウォールで制限する**こと。

```bash
# 家WiFi内アクセス用: 0.0.0.0 バインド（LAN内のみ）
# Windows ファイアウォールでポート8000・3000をLAN内のみ許可すること
uvicorn app.main:app --host 0.0.0.0 --port 8000  # 開発・家WiFi用

# 本番（systemd）: 127.0.0.1バインド + Cloudflare Tunnelで公開
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**AndroidのPWA設定（家WiFi内）:**  
`https://knos.yourdomain.dev` の代わりに `http://192.168.1.x:3000` でアクセス可能。  
ただし PWA の Service Worker は HTTPS 必須なので、家WiFi内は通常ブラウザで使用し、PWAインストールは Cloudflare Tunnel 経由のURLで行う。

#### 4.5.1 Cloudflare Tunnelセットアップ

```bash
# cloudflared インストール
curl -L --output cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# ログイン・トンネル作成
cloudflared tunnel login
cloudflared tunnel create knos
```

```yaml
# ~/.cloudflared/config.yml
tunnel: <TUNNEL_UUID>
credentials-file: ~/.cloudflared/<TUNNEL_UUID>.json
ingress:
  - hostname: knos.yourdomain.dev
    service: http://localhost:3000    # フロントエンド
  - hostname: api.knos.yourdomain.dev
    service: http://localhost:8000    # バックエンドAPI
  - service: http_status:404
```

#### 4.5.2 Cloudflare Accessによる認証

Cloudflare Dashboard → Zero Trust → Access → Applications で設定。

- **ポリシー:** Emails → 自分のGmailアドレスのみ許可
- **対象:** `knos.yourdomain.dev` および `api.knos.yourdomain.dev`

#### 4.5.3 バックエンドでのトークン検証

**AuthProvider抽象化**

Cloudflare Accessは無料・設定が楽だが、「無料で永遠に使える」保証はない。  
認証層をAdapterパターンで隔離し、将来の認証方式変更コストをゼロにする。

```python
# middleware/auth.py

from abc import ABC, abstractmethod

class AuthProvider(ABC):
    @abstractmethod
    async def verify(self, request: Request) -> dict:
        """検証成功→ユーザー情報dict。失敗→HTTPException(401)"""
        ...

class CloudflareAccessProvider(AuthProvider):
    """現在のデフォルト。Cloudflare Access JWT を検証する。"""
    async def verify(self, request: Request) -> dict:
        return await verify_cloudflare_access(request)

class LocalDevProvider(AuthProvider):
    """開発環境専用。DEBUG=true のとき使用。認証を完全スキップ。"""
    async def verify(self, request: Request) -> dict:
        return {"email": "dev@localhost"}

# 将来の拡張候補（実装は不要・インターフェース定義のみ）
# class TailscaleAuthProvider(AuthProvider): ...   # Tailscale SSHキーで認証
# class LocalPasswordProvider(AuthProvider): ...   # ローカルパスワード
# class OAuth2ProxyProvider(AuthProvider): ...     # oauth2-proxy経由

def get_auth_provider() -> AuthProvider:
    if settings.DEBUG:
        return LocalDevProvider()
    return CloudflareAccessProvider()

auth_provider = get_auth_provider()
```

**TunnelProvider抽象化**

外部公開層も同様に抽象化する。Cloudflare Tunnelは現時点で最良の無料選択肢だが、長期的に仕様変更・無料枠変更のリスクがある。

```python
# infrastructure/tunnel.py（設定ファイル・README記載レベルで十分。実装コード不要。）

# 現在: Cloudflare Tunnel（~/.cloudflared/config.yml）
# 将来の移行候補:
#   - Tailscale Funnel（Tailscaleネットワーク経由の公開）
#   - frp（自前サーバーへのリバーストンネル）
#   - ngrok（有料だが安定）
#   - Linuxネイティブ移行後はnginx + Let's Encrypt で直接HTTPS公開

# 移行時に変わるのは:
#   1. ~/.cloudflared/config.yml の設定
#   2. systemd の cloudflared サービス → 代替ツールのサービスに置換
#   3. Cloudflare Access の認証 → AuthProvider を切り替え
# アプリコード（FastAPI・Next.js）は一切変更不要。
```

Cloudflare AccessはすべてのリクエストにJWTを付与する。バックエンドで必ずこれを検証する。

```python
# middleware/auth.py

import asyncio
import httpx
from cachetools import TTLCache
from jose import jwt, JWTError
from fastapi import Request, HTTPException

CERTS_URL = "https://{CF_ACCESS_TEAM}.cloudflareaccess.com/cdn-cgi/access/certs"
AUDIENCE = settings.CF_ACCESS_AUD

# 公開鍵を1時間キャッシュ（毎リクエストでのHTTP呼び出しを防ぐ）
_keys_cache: TTLCache = TTLCache(maxsize=1, ttl=3600)
_cache_lock = asyncio.Lock()

async def get_cloudflare_keys() -> list[dict]:
    """Cloudflare Access の公開鍵を取得。TTL付きキャッシュで1時間保持。"""
    if "keys" in _keys_cache:
        return _keys_cache["keys"]
    async with _cache_lock:
        # ダブルチェック（ロック待ち中に他のタスクが取得済みの場合）
        if "keys" in _keys_cache:
            return _keys_cache["keys"]
        url = CERTS_URL.format(CF_ACCESS_TEAM=settings.CF_ACCESS_TEAM)
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10.0)
            res.raise_for_status()
        keys = res.json()["keys"]
        _keys_cache["keys"] = keys
        return keys

async def verify_cloudflare_access(request: Request) -> dict:
    """
    Cloudflare AccessのJWTを検証する。
    ヘッダー名: Cf-Access-Jwt-Assertion
    開発環境（DEBUG=true）では検証をスキップする。
    """
    if settings.DEBUG:
        return {"email": "dev@localhost"}

    token = request.headers.get("Cf-Access-Jwt-Assertion")
    if not token:
        raise HTTPException(status_code=401, detail="Missing Cf-Access-Jwt-Assertion header")

    try:
        keys = await get_cloudflare_keys()
        payload = jwt.decode(token, keys, algorithms=["RS256"], audience=AUDIENCE)
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
```

### 4.6 環境変数（`.env`）

```env
# ---- App ----
APP_ENV=production          # development | production
DEBUG=false
SECRET_KEY=<random_64chars_hex>
ALLOWED_ORIGINS=https://knos.yourdomain.dev,http://localhost:3000

# ---- Database ----
DATABASE_URL=postgresql+asyncpg://knos:${DB_PASSWORD}@localhost:5432/knos
DATABASE_TEST_URL=postgresql+asyncpg://knos:${DB_PASSWORD}@localhost:5432/knos_test
DB_PASSWORD=<strong_password>

# ---- Storage ----
BLOB_BASE_PATH=/home/<user>/knowledge-os/blobs

# ---- Embedding ----
GEMINI_API_KEY=<your_key>
# gemini-embedding-2-preview: MTEBトップ・MRL対応・マルチモーダル（2026年推奨）
# 次元数3072がフル品質。MRL截断で768にも落とせるが個人規模なら3072推奨。
EMBEDDING_MODEL=gemini-embedding-2-preview
EMBEDDING_DIMENSION=768  # 推奨。3072にする場合はDBマイグレーション必要
EMBEDDING_RATE_LIMIT_RPM=90

# ---- LLM ----
# gemini-2.5-flash: 高速・高品質・無料枠あり（デフォルト）
# gemini-3-flash-preview: 最新・無料枠あり（安定化次第切替）
# ⚠️ Grounding（Google検索）+ JSON構造化出力の同時使用は不可
#    → 二段階処理で回避（後述 Section 7.4）
LLM_PRIMARY_MODEL=gemini-2.5-flash
LLM_FALLBACK_MODEL=gemini-3-flash-preview
# ローカルLLM（ollama）: 空文字でollamaを無効化
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwopus3.5-9b-v3

# ---- Cloudflare Access ----
CF_ACCESS_TEAM=<your-team>
CF_ACCESS_AUD=<application-aud-tag>

# ---- External APIs (フェーズ2以降) ----
NOTION_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
YOUTUBE_API_KEY=               # 実装済みだが当面使用しない
# Playwright fallback（Could・デフォルトfalse）
# trueにする場合は `playwright install chromium` が必要
PLAYWRIGHT_ENABLED=false
```

---

### 4.7 ソフトウェア依存関係仕様（Requirements）

環境構築時の「ライブラリ選定の迷い」と「バージョントラブル」をゼロにするため、設計書内で言及するすべての依存関係をここに集約する。

#### 4.7.1 バックエンド依存関係（`backend/pyproject.toml`）

Python 3.13 のモダンなエコシステムに準拠し、非同期処理（asyncio）と型安全性を最大化するパッケージ群を指定する。

| 分類 | パッケージ名 | バージョン | 用途・選定理由 |
|------|------------|-----------|--------------|
| **コア** | `fastapi` | `^0.136.0` | 拡張性と速度に優れた非同期APIフレームワーク（Pydantic v1サポート終了済み） |
| | `uvicorn[standard]` | `^0.34.0` | 高性能ASGIサーバー（本番・開発常駐用） |
| | `pydantic` | `^2.11.0` | v2による高速なスキーマバリデーション |
| | `pydantic-settings` | `^2.9.0` | 環境変数（`.env`）の一元管理と型安全な読み込み |
| **データ・DB** | `sqlalchemy` | `^2.0.46` | 2.0スタイルの非同期ORM（AsyncSession） |
| | `asyncpg` | `^0.30.0` | PostgreSQL用最速の非同期ドライバー |
| | `alembic` | `^1.15.0` | DBマイグレーション管理 |
| | `GeoAlchemy2` | `^0.15.0` | `entry_place` の PostGIS 空間データ操作 |
| **認証・キャッシュ** | `python-jose[cryptography]` | `^3.3.0` | Cloudflare Access JWT の検証・デコード |
| | `cachetools` | `^5.5.0` | 公開鍵等の TTL 付きインメモリキャッシュ |
| **AI・スクレイパー** | `google-genai` | `^1.66.0` | Google Gen AI SDK（旧`google-generativeai`の後継・2025年11月30日に旧SDKは非推奨化）。`from google import genai` でインポート |
| | `ollama` | `^0.4.0` | ollama Python クライアント（ローカルLLM用・任意） |
| | `httpx` | `^0.28.0` | 外部API呼び出しおよびスクレイパー（一段目） |
| | `trafilatura` | `^2.0.0` | Webページからの高精度な本文・メタデータ抽出 |
| | `curl-cffi` | `^0.10.0` | TLS指紋偽装による高度なBot検知回避スクレイパー |
| | `playwright` | `^1.50.0` | 動的JSサイト用のヘッドレスブラウザスクレイパー |
| **ファイルパース** | `pdfplumber` | `^0.11.0` | レイアウトを維持したPDFテキスト抽出（PyPDF2より高精度） |
| | `python-docx` | `^1.1.0` | Word ドキュメントからのテキスト抽出 |
| | `openpyxl` | `^3.1.5` | Excel シート・セルからのテキスト抽出 |
| | `python-pptx` | `^1.0.0` | PowerPoint スライドからのテキスト抽出 |
| | `beautifulsoup4` | `^4.13.0` | Notion等からエクスポートしたHTMLのパース |
| **ユーティリティ** | `structlog` | `^25.0.0` | JSON形式の構造化ロギング |

インストール（`uv` 推奨）:

```bash
# Python 3.13 を使用すること（3.12以下は非推奨）
uv add fastapi "uvicorn[standard]" pydantic pydantic-settings \
       sqlalchemy asyncpg alembic GeoAlchemy2 \
       "python-jose[cryptography]" cachetools \
       google-genai httpx trafilatura curl-cffi playwright \
       pdfplumber python-docx openpyxl python-pptx beautifulsoup4 \
       structlog ollama

# Playwright はブラウザバイナリの別途インストールが必要
playwright install chromium
# ollama 本体は https://ollama.com からインストール（WSL2対応）
# Qwopus3.5-9B-v3はModelfile登録が必要（Section 7.4.3参照）
```

#### 4.7.2 フロントエンド依存関係（`frontend/package.json`）

Next.js 16 App Router を基軸に、UIの美しさとデータフェッチの摩擦ゼロを両立するライブラリを選定。<br>
⚠️ **Next.js 16 は React 19.2 を要求する。** `create-next-app@16.2.4` が自動インストールするため個別指定不要。

| 分類 | パッケージ名 | バージョン | 用途・選定理由 |
|------|------------|-----------|--------------|
| **フレームワーク** | `next` | `16.2.4` | App Router, Standalone ビルド（systemd用）。最新安定版 |
| | `react` / `react-dom` | `^19.2.0` | Next.js 16が要求するReact 19.2（View Transitions・React Compiler安定化） |
| | `@types/react` | `^19.0.0` | TypeScript型定義 |
| **データフェッチ** | `@tanstack/react-query` | `^5.74.0` | 検索結果のキャッシュ・無限スクロール管理 |
| **状態管理** | `zustand` | `^5.0.0` | クイック追加UIや検索フィルタの状態保持 |
| **グラフ可視化** | `@xyflow/react` | `^12.5.0` | Knowledge Graph 可視化（旧 `reactflow` から改名） |
| **PWA化** | `next-pwa` | `^5.6.0` | Workbox による Service Worker・Android 共有対応 |
| **デザイン・UI** | `tailwindcss` | `^4.1.0` | ユーティリティファーストのスタイリング（v4は設定ファイル不要） |
| | `lucide-react` | `^0.507.0` | 一貫性のあるモダンな型別アイコン群 |
| | `clsx` / `tailwind-merge` | `^2.3.0` | shadcn/ui のコンポーネントクラス結合用 |
| | `@radix-ui/react-*` | 各種最新 | shadcn/ui のベースとなるアクセシブルな各種パーツ |

インストール:

```bash
# ⚠️ Node.js 22 LTS を使用すること（20はMaintenance LTS）
npx create-next-app@16.2.4 frontend --typescript --tailwind --app
cd frontend
npm install @tanstack/react-query zustand @xyflow/react \
            next-pwa lucide-react clsx tailwind-merge \
            @radix-ui/react-dialog @radix-ui/react-dropdown-menu \
            @radix-ui/react-tooltip @radix-ui/react-slot
# React 19.2 は create-next-app が自動インストール
```

#### 4.7.3 `.env.example`

リポジトリルートに配置する。実際の `.env` はこれをコピーして値を埋める。

```env
# ---- App ----
APP_ENV=development          # development | production
DEBUG=true                   # trueのとき認証スキップ（localhostのみ）
SECRET_KEY=change-me-to-random-64-chars-hex
ALLOWED_ORIGINS=http://localhost:3000

# ---- Database ----
DATABASE_URL=postgresql+asyncpg://knos:change-me@localhost:5432/knos
DATABASE_TEST_URL=postgresql+asyncpg://knos:change-me@localhost:5432/knos_test
DB_PASSWORD=change-me

# ---- Storage ----
BLOB_BASE_PATH=/home/YOUR_USERNAME/knowledge-os/blobs

# ---- Embedding ----
GEMINI_API_KEY=your-gemini-api-key
EMBEDDING_MODEL=gemini-embedding-2-preview
EMBEDDING_DIMENSION=768  # 推奨。3072にする場合はDBマイグレーション必要
EMBEDDING_RATE_LIMIT_RPM=90

# ---- LLM ----
LLM_PRIMARY_MODEL=gemini-2.5-flash
LLM_FALLBACK_MODEL=gemini-3-flash-preview
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwopus3.5-9b-v3

# ---- Cloudflare Access ----
CF_ACCESS_TEAM=your-team-name
CF_ACCESS_AUD=your-application-aud-tag

# ---- External APIs (フェーズ2以降・空でも起動可) ----
NOTION_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
YOUTUBE_API_KEY=             # 実装済み・空のとき503を返す
PLAYWRIGHT_ENABLED=false     # trueにする場合は playwright install chromium が必要
```

---

## 5. データモデル仕様

### 5.1 設計パターン

**Class Table Inheritance** を採用する。

- `entry` テーブルがすべての型の共通フィールドを持つ
- 各型専用の拡張テーブル（`entry_webpage` 等）が `entry.id` を外部キーとして持つ
- Brain Layer（embedding・connection・tag）はすべて `entry.id` を参照する
- これにより「型に関わらず全entryが検索・接続・タグの対象になる」を実現する

### 5.2 entry_type — 参照テーブル（マスターデータ）

PostgreSQL `ENUM` は型の追加に `ALTER TYPE`（トランザクション外実行が必要）が必要で長期運用に不向きなため、参照テーブルを採用する。アプリケーション層でENUM相当のバリデーションを行う。

```sql
-- name をPKにする。id(SMALLSERIAL)は不要（nameで直接FK参照するため）。
-- 新しい型の追加は INSERT 1行で完結し、ALTER TYPE 不要。
CREATE TABLE entry_type (
    name        TEXT PRIMARY KEY,               -- 'webpage', 'thought', etc.
    label_ja    TEXT NOT NULL,                  -- 表示名（日本語）
    icon        TEXT,                           -- アイコン識別子（フロント用）
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,  -- 無効化で論理的に非表示にできる
    sort_order  SMALLINT NOT NULL DEFAULT 0
);

-- 初期データ
INSERT INTO entry_type (name, label_ja, icon, sort_order) VALUES
    ('webpage',    'Webページ',  'globe',        1),
    ('thought',    '思考メモ',   'brain',        2),
    ('book',       '書籍',       'book',         3),
    ('video',      '動画',       'video',        4),
    ('document',   'ドキュメント','document',    5),
    ('media',      'メディア',   'image',        6),
    ('person',     '人物',       'user',         7),
    ('org',        '組織',       'building',     8),
    ('place',      '場所',       'map-pin',      9),
    ('event',      '出来事',     'calendar',     10),
    ('definition', '定義・用語', 'book-open',    11),
    ('liked',      'Liked',      'heart',        12),
    ('ai_conv',    'AI会話',     'message-bot',  13);
```

新しい型の追加は `INSERT` 1行で完結する。

### 5.3 entryテーブル（共通ベース）

```sql
CREATE TABLE entry (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type          TEXT NOT NULL REFERENCES entry_type(name),
    title         TEXT NOT NULL,
    content       TEXT,           -- 型に依存しない「ユーザーが書いたメモ・注釈」のみ
                                  -- 型固有のテキスト（full_text等）は拡張テーブルへ
    summary       TEXT,           -- AI生成サマリー（任意）
    source_url    TEXT,
    lang          CHAR(10),       -- BCP 47形式（例: 'ja', 'en', 'zh-TW'）
                                  -- 検索時の言語切替・表示のみに使用
    is_favorite   BOOLEAN NOT NULL DEFAULT FALSE,
    -- ノイズ管理: 削除せず検索ランキングから降格させる
    -- 一時メモ・スクラップURL・AI会話ログが増えても「人生のゴミ箱」化しないための仕組み
    is_muted      BOOLEAN NOT NULL DEFAULT FALSE,
    -- 再閲覧日時: temporal relevance の計算に使用（recency score）
    accessed_at   TIMESTAMPTZ,
    deleted_at    TIMESTAMPTZ,    -- 論理削除。NULLで有効、値ありで削除済み
    -- `metadata` 使用ガイドライン:
    -- 「型別拡張テーブルにカラムを追加するほどではない、ソース固有の補助情報」を格納する。
    -- 検索・フィルタの主軸には使わない（主軸は拡張テーブルのカラムで対応する）。
    -- 使用例:
    --   {"notion_id": "abc123", "notion_last_edited": "2025-01-01T00:00:00Z"}
    --   {"imported_from": "obsidian", "original_vault": "main", "original_path": "notes/ai/transformer.md"}
    --   {"x_tweet_id": "123456", "x_retweet_count": 42}
    --   {"import_batch_id": "batch_2025-05-04"}
    metadata      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()  -- トリガーで自動更新
);

-- updated_at自動更新トリガー
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_entry_updated_at
    BEFORE UPDATE ON entry
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- インデックス
CREATE INDEX idx_entry_type         ON entry(type);
CREATE INDEX idx_entry_created_at   ON entry(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_entry_accessed_at  ON entry(accessed_at DESC) WHERE accessed_at IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX idx_entry_is_favorite  ON entry(is_favorite)     WHERE is_favorite = TRUE;
CREATE INDEX idx_entry_is_muted     ON entry(is_muted)        WHERE is_muted = TRUE;
CREATE INDEX idx_entry_deleted_at   ON entry(deleted_at)      WHERE deleted_at IS NOT NULL;
CREATE INDEX idx_entry_metadata     ON entry USING GIN(metadata);

-- pgroonga全文検索インデックス（日本語対応）
-- 削除: search_document に集約。下記インデックスは使用しない。
-- CREATE INDEX idx_entry_pgroonga
--     ON entry USING pgroonga (title, content)
    WITH (tokenizer='TokenNgram("unify_symbol", false, "unify_digit", false)');
```

**`entry.content` の役割（明確化）:**  
「ユーザーが入力した注釈・コメント・感想」のみを格納する。型固有のテキスト（スクレイプ全文・ドキュメント抽出テキスト等）は拡張テーブルに持つ。これによりcontentはユーザーの声を保持し、検索ノイズが減る。

### 5.4 型別拡張テーブル

#### 5.4.1 `entry_webpage`

```sql
CREATE TABLE entry_webpage (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    url             TEXT NOT NULL CHECK (url ~ '^https?://[^/]+'),
    -- 生成列。アプリケーション層で url が http:// or https:// 始まりを必ず検証してから
    -- INSERT すること（ftp:// 等には非対応）。
    domain          TEXT NOT NULL GENERATED ALWAYS AS (
                        regexp_replace(url, '^https?://([^/]+).*$', '\1')
                    ) STORED,
    scraped_at      TIMESTAMPTZ,
    full_text       TEXT,           -- スクレイプ全文（検索用）
    thumbnail_path  TEXT,           -- blobs/からの相対パス
    reading_time_s  INTEGER,        -- 推定読了時間（秒）
    author          TEXT,
    published_at    TIMESTAMPTZ,
    -- ユーザーメモは entry.content に統一。user_note カラムは持たない。
    scraper_used    TEXT            -- 'httpx+trafilatura' | 'curl_cffi' | 'playwright'
);

CREATE INDEX idx_webpage_domain ON entry_webpage(domain);
-- 削除: search_document に集約。
-- CREATE INDEX idx_webpage_pgroonga ON entry_webpage USING pgroonga (full_text);
```

#### 5.4.2 `entry_thought`

```sql
CREATE TABLE entry_thought (
    entry_id    UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    mood        TEXT,
    context     TEXT,
    is_draft    BOOLEAN NOT NULL DEFAULT FALSE
);
```

#### 5.4.3 `entry_book`

```sql
CREATE TABLE entry_book (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    isbn            TEXT,
    authors         TEXT[],
    publisher       TEXT,
    published_year  INTEGER,
    total_pages     INTEGER,
    read_status     TEXT NOT NULL DEFAULT 'unread'
                    CHECK (read_status IN ('unread','reading','done','dropped')),
    read_start_date DATE,
    read_end_date   DATE,
    rating          SMALLINT CHECK (rating BETWEEN 1 AND 5),
    cover_path      TEXT
);
```

#### 5.4.4 `entry_video`

```sql
CREATE TABLE entry_video (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    platform        TEXT NOT NULL,
    video_id        TEXT,
    channel_name    TEXT,
    channel_id      TEXT,
    duration_s      INTEGER,
    thumbnail_url   TEXT,
    transcript      TEXT,
    watched_at      TIMESTAMPTZ,
    watch_progress  REAL CHECK (watch_progress BETWEEN 0 AND 1)
);

-- 削除: search_document に集約。
-- CREATE INDEX idx_video_pgroonga ON entry_video USING pgroonga (transcript);
```

#### 5.4.5 `entry_document`

```sql
CREATE TABLE entry_document (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    doc_type        TEXT NOT NULL
                    CHECK (doc_type IN ('pdf','docx','xlsx','pptx','gdoc','gsheet','gslides','txt','md','other')),
    blob_path       TEXT,               -- ローカルblobs/相対パス（ローカルファイル）
    gdrive_id       TEXT,               -- Google Drive File ID
    gdrive_url      TEXT,               -- GDriveの共有URL
    gdrive_mime     TEXT,               -- GDriveのMIMEタイプ
    mime_type       TEXT NOT NULL,
    file_size_bytes BIGINT,
    page_count      INTEGER,
    extracted_text  TEXT,               -- テキスト抽出済み（検索用）
    extraction_method TEXT,             -- 'pdfplumber' | 'python-docx' | 'gdrive-export' | etc.
    version         TEXT,
    CONSTRAINT chk_blob_or_gdrive
        CHECK (blob_path IS NOT NULL OR gdrive_id IS NOT NULL)
);

-- 削除: search_document に集約。
-- CREATE INDEX idx_document_pgroonga ON entry_document USING pgroonga (extracted_text);
```

#### 5.4.6 `entry_media`

```sql
CREATE TABLE entry_media (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    media_type      TEXT NOT NULL CHECK (media_type IN ('image','audio','video_file','other')),
    blob_path       TEXT NOT NULL,
    mime_type       TEXT NOT NULL,
    file_size_bytes BIGINT,
    width_px        INTEGER,
    height_px       INTEGER,
    duration_s      REAL,
    ocr_text        TEXT,               -- Gemini Vision API によるOCR結果
    caption         TEXT
);
```

#### 5.4.7 `entry_person`

```sql
CREATE TABLE entry_person (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    full_name       TEXT NOT NULL,
    aliases         TEXT[],
    birth_year      INTEGER,
    death_year      INTEGER,
    nationality     TEXT,
    occupations     TEXT[],
    biography       TEXT,
    photo_path      TEXT
);
```

#### 5.4.8 `entry_org`

```sql
CREATE TABLE entry_org (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    official_name   TEXT NOT NULL,
    aliases         TEXT[],
    org_type        TEXT,               -- '企業', '大学', 'NGO', '政府機関', etc.
    founded_year    INTEGER,
    country         TEXT,
    website_url     TEXT,
    description     TEXT
);
```

#### 5.4.9 `entry_place`

```sql
CREATE TABLE entry_place (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    place_name      TEXT NOT NULL,
    place_type      TEXT,               -- '駅', '建物', '地域', '施設', etc.
    address         TEXT,
    location        GEOMETRY(Point, 4326),  -- PostGIS Point (WGS84)
    osm_id          TEXT,
    visited_dates   DATE[],             -- 訪問記録
    photo_paths     TEXT[]
);

-- PostGIS 空間インデックス
CREATE INDEX idx_place_location ON entry_place USING GIST(location);
```

#### 5.4.10 `entry_event`

```sql
CREATE TABLE entry_event (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    event_name      TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ,
    location_text   TEXT,
    place_entry_id  UUID REFERENCES entry(id),   -- entry_placeとの紐付け（任意）
    is_personal     BOOLEAN NOT NULL DEFAULT TRUE,
    participants    TEXT[],
    outcome         TEXT
);

CREATE INDEX idx_event_started_at ON entry_event(started_at DESC);
```

#### 5.4.11 `entry_definition`

SRS状態は `srs_review` 履歴から計算するため、`entry_definition` には持たない。`next_review_at` は `srs_review` テーブルの最新レコードから導出する。

```sql
CREATE TABLE entry_definition (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    term            TEXT NOT NULL,
    reading         TEXT,               -- ふりがな・読み仮名
    definition      TEXT NOT NULL,
    field           TEXT,               -- '数学', 'CS', '経済学', '物理', etc.
    examples        TEXT[],
    related_terms   TEXT[]
);
```

#### 5.4.12 `entry_liked`

**設計方針:** `entry_liked` は「元プラットフォームでの Like/ブックマークという行為の記録」に特化する。  
コンテンツが動画であれば `entry_video`、Webページであれば `entry_webpage` に変換してインポートする方が正規化される。  
フェーズ4のインポート実装時に、変換できるものは適切な型に変換し、`entry_liked` は変換できなかったコンテンツ（プラットフォーム固有形式等）の受け皿とする。

```sql
CREATE TABLE entry_liked (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    platform        TEXT NOT NULL,      -- 'youtube' | 'x' | 'instagram' | etc.
    original_id     TEXT NOT NULL,
    liked_at        TIMESTAMPTZ,
    content_type    TEXT NOT NULL,      -- 'video' | 'post' | 'image' | etc.
    author_name     TEXT,
    author_handle   TEXT,
    thumbnail_url   TEXT,
    full_text       TEXT,               -- 本文・動画説明
    UNIQUE (platform, original_id)
);
```

#### 5.4.13 `entry_ai_conv`

```sql
CREATE TABLE entry_ai_conv (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    model           TEXT NOT NULL,      -- 'claude-sonnet-4-6', 'gemini-2.0-flash', etc.
    provider        TEXT NOT NULL,      -- 'anthropic' | 'google' | 'openai' | 'local'
    messages        JSONB NOT NULL DEFAULT '[]',
    token_count     INTEGER,
    topic           TEXT,
    is_useful       BOOLEAN
);

-- messages JSONB スキーマ（各要素の定義）
-- [
--   {
--     "role":      "user" | "assistant" | "system",
--     "content":   string,                   // テキスト内容
--     "timestamp": "2025-05-04T12:00:00Z",   // ISO 8601
--     "tokens":    integer | null            // トークン数（任意）
--   },
--   ...
-- ]

-- 削除: search_document に集約。
-- CREATE INDEX idx_ai_conv_messages_pgroonga
--     ON entry_ai_conv USING pgroonga ((messages::text));
```

### 5.5 横断テーブル（Brain Layer）

#### 5.5.0 `search_document` — 全文検索・Embedding入力の集約テーブル

全文検索対象テキストは型別拡張テーブルに分散している（`entry_webpage.full_text`、`entry_document.extracted_text` 等）。  
これを毎回JOINして検索すると **インデックス複数・ランキング複雑化・重複結果** が発生する。  
`search_document` テーブルに全entryの検索用テキストを集約することで、検索クエリを単純化しEmbedding生成の入力も一元化する。

```sql
CREATE TABLE search_document (
    entry_id        UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    -- 全型のテキストをここに集約。build_embedding_text()と同じロジックで生成。
    combined_text   TEXT NOT NULL,
    lang            CHAR(10) NOT NULL DEFAULT 'ja',   -- entry.langと同期
    -- 検索ウェイト（将来のBM25チューニング用）
    -- {"title": 3.0, "content": 2.0, "full_text": 1.0} のような形式
    weight_json     JSONB NOT NULL DEFAULT '{}',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- pgroonga全文検索インデックス（単一・高速）
CREATE INDEX idx_search_document_pgroonga
    ON search_document USING pgroonga (combined_text)
    WITH (tokenizer='TokenNgram("unify_symbol", false, "unify_digit", false)');

-- updated_at自動更新トリガー
CREATE TRIGGER trg_search_document_updated_at
    BEFORE UPDATE ON search_document
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

**`search_document` のライフサイクル:**
- entry 作成・更新時に非同期で `combined_text` を生成・upsert する
- Embedding生成（`call_gemini_embedding()`）も `combined_text` を入力として使用する（重複計算なし）
- entry 削除時は CASCADE で自動削除される

**これによって廃止できるインデックス:**
- `idx_entry_pgroonga`（`entry.title + content`）
- `idx_webpage_pgroonga`（`entry_webpage.full_text`）
- `idx_video_pgroonga`（`entry_video.transcript`）
- `idx_document_pgroonga`（`entry_document.extracted_text`）
- `idx_ai_conv_messages_pgroonga`（`entry_ai_conv.messages`）

→ 上記5つのpgroognaインデックスをすべて削除し、`search_document` の1インデックスに集約する。

#### 5.5.1 `embedding`

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE embedding (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id    UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    -- デフォルト768次元（MRL截断推奨・個人規模に最適）。
    -- 3072に変更する場合は EMBEDDING_DIMENSION=768  # 推奨。3072にする場合はDBマイグレーション必要 に変更しマイグレーションが必要。
    vector      vector(768) NOT NULL,
    model       TEXT NOT NULL DEFAULT 'gemini-embedding-2-preview',
    input_text  TEXT NOT NULL,          -- search_document.combined_text と同じ内容
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- HNSWインデックス（コサイン類似度）
-- 768次元・個人規模ではm=16・ef_construction=64で十分。
CREATE INDEX idx_embedding_hnsw
    ON embedding USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE UNIQUE INDEX idx_embedding_entry_id ON embedding(entry_id);
```

#### 5.5.2 `connection`

有向・無向の混在問題を `is_directed` カラム＋トリガーで解決する。  
`connection_type_def` から `is_directed` をINSERT時にコピーし、部分インデックスの WHERE 句で静的に参照する。  
**注意:** PostgreSQL の部分インデックス WHERE 句ではサブクエリが使えないため、型名を静的リストで指定する。新しい `connection_type_def` を追加した場合はインデックスを `DROP → CREATE` で更新する（頻度低・許容範囲）。

```sql
CREATE TABLE connection_type_def (
    name             TEXT PRIMARY KEY,
    label_ja         TEXT NOT NULL,
    is_directed      BOOLEAN NOT NULL,   -- TRUE: 有向（A→B ≠ B→A）、FALSE: 無向
    -- 有向型のバックリンク表示用逆ラベル（Graph・詳細画面で「Bから見たAとの関係」を表示）
    -- 例: references → referenced_by（「このページを参照しているエントリー」）
    -- 無向型はNULL
    inverse_label_ja TEXT
);

INSERT INTO connection_type_def VALUES
    ('related',      '関連',   FALSE, NULL),
    ('references',   '参照',   TRUE,  '被参照'),
    ('contradicts',  '矛盾',   FALSE, NULL),
    ('extends',      '拡張',   TRUE,  '拡張元'),
    ('exemplifies',  '例示',   TRUE,  '例示元'),
    ('authored_by',  '著者',   TRUE,  '著作'),
    ('published_by', '発行元', TRUE,  '刊行物'),
    ('located_at',   '場所',   TRUE,  '関連エントリー'),
    ('occurred_at',  '出来事', TRUE,  '関連エントリー');

CREATE TABLE connection (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_a_id      UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    entry_b_id      UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    relation_type   TEXT NOT NULL REFERENCES connection_type_def(name),
    strength        REAL NOT NULL DEFAULT 0.5 CHECK (strength BETWEEN 0 AND 1),
    note            TEXT,
    is_auto         BOOLEAN NOT NULL DEFAULT FALSE,
    -- INSERT時にトリガーで connection_type_def.is_directed をコピー。
    -- DEFAULTは意図的に設定しない。トリガーが発火しなければ NOT NULL 違反で即失敗し気づける。
    is_directed     BOOLEAN NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 無向関係の正規化ペア（LEAST/GREATEST で常に小さいUUIDをaに）
    canonical_a     UUID GENERATED ALWAYS AS (
                        LEAST(entry_a_id, entry_b_id)
                    ) STORED,
    canonical_b     UUID GENERATED ALWAYS AS (
                        GREATEST(entry_a_id, entry_b_id)
                    ) STORED,

    CONSTRAINT chk_no_self_loop CHECK (entry_a_id <> entry_b_id)
);

-- is_directed を connection_type_def から自動コピーするトリガー（INSERT・UPDATE両対応）
CREATE OR REPLACE FUNCTION fill_connection_is_directed()
RETURNS TRIGGER AS $$
BEGIN
    SELECT is_directed INTO NEW.is_directed
    FROM connection_type_def
    WHERE name = NEW.relation_type;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_connection_is_directed
    BEFORE INSERT OR UPDATE OF relation_type ON connection
    FOR EACH ROW EXECUTE FUNCTION fill_connection_is_directed();

-- 無向関係の重複防止（静的リスト指定。サブクエリ不可のため）
-- 無向型: related, contradicts
CREATE UNIQUE INDEX idx_connection_undirected
    ON connection (canonical_a, canonical_b, relation_type)
    WHERE NOT is_directed;

-- 有向関係の重複防止
-- 有向型: references, extends, exemplifies, authored_by, published_by, located_at, occurred_at
CREATE UNIQUE INDEX idx_connection_directed
    ON connection (entry_a_id, entry_b_id, relation_type)
    WHERE is_directed;

CREATE INDEX idx_connection_entry_a ON connection(entry_a_id);
CREATE INDEX idx_connection_entry_b ON connection(entry_b_id);
```

#### 5.5.2b `connection_candidate` — 接続候補（ユーザー承認待ち）

自動接続を直接 `connection` に書き込まず、まず `connection_candidate` に積む。  
ユーザーがUIで承認した時点で `connection` に昇格する。却下されたものは `status='rejected'` となり再提案しない。  
これにより「汎用語による接続爆発・Graph毛玉化」を防ぐ。

```sql
CREATE TABLE connection_candidate (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_a_id      UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    entry_b_id      UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    similarity      REAL NOT NULL CHECK (similarity BETWEEN 0 AND 1),
    suggested_type  TEXT NOT NULL DEFAULT 'related'
                    REFERENCES connection_type_def(name),
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected')),
    -- 承認 → connection が作成され connection_id に記録
    connection_id   UUID REFERENCES connection(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at     TIMESTAMPTZ,

    CONSTRAINT chk_no_self_loop CHECK (entry_a_id <> entry_b_id),
    -- 同ペアの重複候補を防ぐ（canonical_a/bで正規化）
    UNIQUE (LEAST(entry_a_id, entry_b_id), GREATEST(entry_a_id, entry_b_id))
);

CREATE INDEX idx_candidate_pending ON connection_candidate(created_at DESC)
    WHERE status = 'pending';
CREATE INDEX idx_candidate_entry_a ON connection_candidate(entry_a_id);
CREATE INDEX idx_candidate_entry_b ON connection_candidate(entry_b_id);
```

**接続候補の昇格フロー:**
```
entry作成
    ↓ 非同期
generate_connection_candidates()   ← AUTO_CONNECT_ENABLEDがTRUEのとき
    ↓
connection_candidate (status='pending') に積む
    ↓ ユーザーがUIで確認
承認 → create_connection() → connection_id にリンク → status='approved'
却下 → status='rejected'（同ペアは再提案しない）
```

#### 5.5.3 `tag` と `topic`

```sql
CREATE TABLE topic (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    slug        TEXT NOT NULL UNIQUE,
    parent_id   UUID REFERENCES topic(id) ON DELETE SET NULL,
    description TEXT,
    color       CHAR(7),                -- '#RRGGBB'
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE tag (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    slug        TEXT NOT NULL UNIQUE,
    color       CHAR(7),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE entry_topic (
    entry_id    UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    topic_id    UUID NOT NULL REFERENCES topic(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, topic_id)
);

CREATE TABLE entry_tag (
    entry_id    UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    tag_id      UUID NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, tag_id)
);

CREATE INDEX idx_entry_topic_topic ON entry_topic(topic_id);
CREATE INDEX idx_entry_tag_tag     ON entry_tag(tag_id);
```

#### 5.5.4 `srs_review`（Spaced Repetition 復習記録）

SRSの現在状態（次回復習日・レベル）は `srs_review` の最新レコードから計算する。`entry_definition` には持たない。

```sql
CREATE TABLE srs_review (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id        UUID NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    reviewed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    grade           SMALLINT NOT NULL CHECK (grade BETWEEN 0 AND 5),
                    -- SM-2グレード:
                    -- 0: 完全忘却（即再試行）
                    -- 1: 誤り（即再試行）
                    -- 2: 誤りだが思い出した
                    -- 3: 正解（難）
                    -- 4: 正解
                    -- 5: 完璧
    interval_days   INTEGER NOT NULL,
    ease_factor     REAL    NOT NULL DEFAULT 2.5,
    next_review_at  TIMESTAMPTZ NOT NULL  -- 次回復習日時
);

CREATE INDEX idx_srs_entry     ON srs_review(entry_id);
CREATE INDEX idx_srs_next_review ON srs_review(next_review_at)
    WHERE next_review_at <= NOW() + INTERVAL '7 days';

-- SRS現在状態を取得するビュー
CREATE VIEW srs_current AS
SELECT DISTINCT ON (entry_id)
    entry_id,
    grade,
    interval_days,
    ease_factor,
    next_review_at,
    reviewed_at AS last_reviewed_at
FROM srs_review
ORDER BY entry_id, reviewed_at DESC;

-- `GET /srs/due` はこのビューを使って以下のクエリで本日分を取得する:
--
-- SELECT sc.*, e.title, e.type
-- FROM srs_current sc
-- JOIN entry e ON e.id = sc.entry_id
-- WHERE sc.next_review_at <= NOW()
--   AND e.deleted_at IS NULL
-- ORDER BY sc.next_review_at ASC;
--
-- entry_definition に srs_level は持たない。SRS状態はすべてこのビューから計算する。
```

---

## 6. ストレージ戦略

### 6.1 ファイル保存方針

実ファイルはローカルファイルシステムに保存。DBにはパスのみを格納する。

**命名規則:** `{entry_id[:8]}_{sanitized_original_name}`  
例: `a1b2c3d4_transformer_paper.pdf`

```
~/knowledge-os/blobs/
├── documents/
│   └── YYYY/           ← 年別サブディレクトリ
├── media/
│   ├── images/
│   └── audio/
└── tmp/                ← インポート処理中（完了後削除）
```

### 6.2 Google Drive連携方針

GDriveファイルはローカルにダウンロードしない。DBに以下を記録する。

- `gdrive_id`: ファイルID（取得・更新時に使用）
- `gdrive_url`: 共有URL（ブラウザで直接開くため）
- `extracted_text`: テキスト内容のキャッシュ（検索・Embedding用、更新日時チェック付き）

### 6.3 バックアップ戦略

#### 6.3.1 PostgreSQL → GitHub バックアップ（毎日 cron）

```bash
#!/bin/bash
# scripts/backup.sh
# ⚠️ このシステムには人生ログ（思考・AI会話・URL履歴・PDF）が入る。
#    GitHubにpushする前に必ず age で暗号化すること。
#    token漏洩・誤push時のデータ露出を防ぐ。

set -euo pipefail

BACKUP_DIR=~/knowledge-os-backup
DATE=$(date +%Y%m%d)
AGE_RECIPIENT=~/.config/knos/backup.pub   # age公開鍵

# age が未インストールの場合: sudo apt install age
if ! command -v age &>/dev/null; then
    echo "ERROR: age not installed. Run: sudo apt install age"
    exit 1
fi

# PGダンプ → age暗号化
pg_dump -U knos knos | gzip | \
    age --recipient-file "${AGE_RECIPIENT}" \
    > "${BACKUP_DIR}/knos_${DATE}.sql.gz.age"

# 古いバックアップを30日分のみ保持
find "${BACKUP_DIR}" -name "*.sql.gz.age" -mtime +30 -delete

# GitHubへpush（暗号化済みファイルのみ）
cd "${BACKUP_DIR}"
git add -A
git commit -m "backup: ${DATE}" || echo "Nothing to commit"
git push origin main

echo "Encrypted backup completed: ${DATE}"
```

**初回セットアップ（age鍵生成）:**
```bash
sudo apt install age
mkdir -p ~/.config/knos
age-keygen -o ~/.config/knos/backup-key.txt
# 公開鍵を取り出して backup.pub に保存
grep "public key:" ~/.config/knos/backup-key.txt | awk '{print $NF}' > ~/.config/knos/backup.pub
# ⚠️ backup-key.txt（秘密鍵）は絶対にGit管理しないこと
echo "~/.config/knos/backup-key.txt" >> ~/.gitignore_global
```

**復元方法:**
```bash
# 暗号化バックアップの復元
age --decrypt -i ~/.config/knos/backup-key.txt \
    knos_20260504.sql.gz.age | gunzip | psql -U knos knos
```

#### 6.3.2 PostgreSQL → SQLite 可搬バックアップ

可搬性のためにSQLiteへの変換スクリプトを整備する。PGダンプのみに依存しない二重安全網。

```python
# scripts/export_sqlite.py

import sqlite3
import asyncpg
import asyncio
import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

TABLES_TO_EXPORT = [
    "entry_type", "entry", "entry_webpage", "entry_thought", "entry_book",
    "entry_video", "entry_document", "entry_media", "entry_person",
    "entry_org", "entry_place", "entry_event", "entry_definition",
    "entry_liked", "entry_ai_conv", "connection",
    "connection_type_def", "tag", "topic", "entry_tag", "entry_topic",
    "srs_review", "search_document"
    # embedding は vector型をTEXTに変換するため別処理
]

def serialize_value(v) -> str | None:
    """
    PostgreSQLの型をSQLiteのTEXT/REAL/INTEGERに安全に変換する。
    str(v) でそのまま変換すると JSON・timestamp・UUID が壊れる場合があるため
    型を明示的に判定して変換する。
    """
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, default=str)  # JSONB → JSON文字列
    if isinstance(v, (datetime,)):
        return v.isoformat()            # timestamptz → ISO 8601文字列
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, uuid.UUID):
        return str(v)                   # UUID → 文字列
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (bytes, bytearray)):
        return v.hex()                  # bytea → hex文字列
    # vector型（list[float]）は embedding テーブルのみ・別処理
    return str(v)

async def export_to_sqlite(sqlite_path: str):
    conn = await asyncpg.connect(DATABASE_URL)
    sqlite = sqlite3.connect(sqlite_path)

    # スキーマバージョン・カラム型情報を保存（復元時のパース手助け用）
    sqlite.execute("""
        CREATE TABLE IF NOT EXISTS _schema_meta (
            table_name TEXT NOT NULL,
            column_name TEXT NOT NULL,
            pg_type TEXT NOT NULL,
            PRIMARY KEY (table_name, column_name)
        )
    """)
    sqlite.execute("CREATE TABLE IF NOT EXISTS _export_info (key TEXT PRIMARY KEY, value TEXT)")
    sqlite.execute("INSERT OR REPLACE INTO _export_info VALUES ('exported_at', ?)",
                   (datetime.now().isoformat(),))
    sqlite.execute("INSERT OR REPLACE INTO _export_info VALUES ('schema_version', '3.0')")

    for table in TABLES_TO_EXPORT:
        # カラム型情報をpg_attributeから取得
        col_info = await conn.fetch("""
            SELECT attname, pg_catalog.format_type(atttypid, atttypmod)
            FROM pg_attribute
            WHERE attrelid = $1::regclass AND attnum > 0 AND NOT attisdropped
            ORDER BY attnum
        """, table)
        for col in col_info:
            sqlite.execute(
                "INSERT OR REPLACE INTO _schema_meta VALUES (?, ?, ?)",
                (table, col['attname'], col['pg_catalog.format_type'])
            )

        rows = await conn.fetch(f"SELECT * FROM {table}")
        if not rows:
            continue
        columns = list(rows[0].keys())
        sqlite.execute(
            f"CREATE TABLE IF NOT EXISTS {table} "
            f"({', '.join(f'{c} TEXT' for c in columns)})"
        )
        for row in rows:
            values = [serialize_value(v) for v in row.values()]
            sqlite.execute(
                f"INSERT OR REPLACE INTO {table} VALUES ({', '.join('?' * len(columns))})",
                values
            )

    # embedding は vector型のみ JSON配列として格納（復元可能な形式）
    emb_rows = await conn.fetch("SELECT entry_id, model, input_text, created_at FROM embedding")
    sqlite.execute("""
        CREATE TABLE IF NOT EXISTS embedding_meta
        (entry_id TEXT, model TEXT, input_text TEXT, created_at TEXT)
    """)
    for row in emb_rows:
        sqlite.execute("INSERT OR REPLACE INTO embedding_meta VALUES (?,?,?,?)",
                       [serialize_value(v) for v in row.values()])
    # vectorデータはSQLiteに入れない（サイズが大きく・SQLiteで使えないため）
    # 必要なら embedding.input_text から再生成可能

    sqlite.commit()
    sqlite.close()
    await conn.close()
    print(f"Exported to {sqlite_path}")

if __name__ == "__main__":
    asyncio.run(export_to_sqlite(f"knos_export_{__import__('datetime').date.today()}.sqlite"))
```

SQLiteファイルには `_schema_meta`（カラムのPG型情報）と `_export_info`（エクスポート日時・スキーマバージョン）が含まれるため、将来の復元・移行時にパースが容易になる。

### 6.4 データ永続性の保証（3層）

| 層 | 媒体 | 頻度 |
|---|------|------|
| 第1層 | WSL2ローカルPostgreSQL | リアルタイム |
| 第2層 | GitHubプライベートリポジトリ（SQLダンプ） | 毎日 |
| 第3層 | SQLiteファイル（blobs含む外付けドライブ） | 週次推奨 |

---

## 7. Brain Layer仕様

### 7.1 Embedding Engine

#### 7.1.1 モデル仕様

| 項目 | 値 |
|------|-----|
| モデル | Gemini `gemini-embedding-2-preview` |
| 推奨次元数 | **768**（MRL截断・個人規模に最適） |
| 最大次元数 | 3072（フル品質・後述） |
| 最大入力トークン | 2048 |
| 対応モダリティ | テキスト・画像・動画・音声・PDF（マルチモーダル） |
| 無料枠 | Google AI Studio APIキーで利用可（クレカ不要） |

**次元数の選択指針:**

| 次元数 | 推奨タイミング | 特徴 |
|--------|-------------|------|
| **768** | **フェーズ1〜3（推奨デフォルト）** | ストレージ・RAM・HNSW rebuild が4分の1。個人規模・日本語主体では3072との品質差は小さい |
| 3072 | フェーズ4以降、必要と感じてから | フル品質。数十万件規模では RAM・vacuumコストが体感できるレベルで重くなる |

**MRL截断の設定方法（768次元に変更する場合）:**
```env
EMBEDDING_DIMENSION=768
```
APIパラメータ `output_dimensionality: 768` で截断。DBの `vector(768)` に合わせること。  
**フェーズ1は768で開始し、必要を感じたらマイグレーションで3072に拡張する**のが安全。

#### 7.1.2 型別 Indexing Strategy（検索品質の核心）

**重要:** 検索品質を決めるのはアルゴリズムより「何をEmbeddingに食わせるか」。  
boilerplate・ナビゲーション・広告テキストをそのまま入れると、類似度が汚染される。

| 型 | Embedding入力テキストの構築方針 | 注意点 |
|----|--------------------------|--------|
| `webpage` | `title + content(ユーザーメモ) + full_text[:1500]` | trafilaturaがboilerprate除去済みのためそのまま使える。全文をそのまま入れない |
| `thought` | `title + content` | ユーザーの思考そのものが価値。加工不要 |
| `book` | `title + authors + content(読書メモ)` | 書誌情報より読書メモが核心。abstractやあらすじは不要 |
| `video` | `title + channel + content(メモ) + transcript[:1000]` | 字幕は最初の1000文字（イントロ）が最も内容を表す |
| `document` | `title + content(メモ) + extracted_text[:1500]` | PDFは先頭より中間部分が価値あることが多い→将来的にチャンク化を検討 |
| `definition` | `term + ": " + definition + examples[:3].join(", ")` | 定義文そのものが最重要。用例は補助 |
| `person` | `full_name + occupations + biography[:300]` | 肩書・略歴の前半が識別情報として最も強い |
| `place` | `place_name + place_type + address + content` | 地名・種別・住所の組み合わせが最良 |
| `event` | `event_name + started_at.year + location + content` | 時期と場所を含めることで時系列検索の精度が上がる |
| `ai_conv` | `topic + userメッセージの先頭と末尾` | assistant応答は含めない。自分の思考（userターン）のみ |
| `liked` | `platform + author + title + full_text[:500]` | プラットフォームと著者名を先頭に置くことで絞り込み精度向上 |

```python
def build_embedding_text(entry: EntryWithExtension) -> str:
    parts = [entry.title]
    # ユーザーのメモは全型で最優先（自分の声）
    if entry.content:
        parts.append(entry.content)

    match entry.type:
        case "webpage":
            # boilerplate除去済みのtrafilatura出力を使用
            if entry.ext.full_text:
                parts.append(entry.ext.full_text[:1500])
        case "thought":
            pass  # title + content で完結
        case "book":
            if entry.ext.authors:
                parts.append(" / ".join(entry.ext.authors))
            # 書誌情報より読書メモ(content)が核心 → 既に追加済み
        case "video":
            if entry.ext.channel_name:
                parts.append(entry.ext.channel_name)
            if entry.ext.transcript:
                parts.append(entry.ext.transcript[:1000])  # イントロ部分のみ
        case "document":
            if entry.ext.extracted_text:
                # PDFは先頭より全体をスライドさせる（将来: chunk化を検討）
                parts.append(entry.ext.extracted_text[:1500])
        case "definition":
            parts.append(entry.ext.definition)
            if entry.ext.examples:
                parts.extend(entry.ext.examples[:3])
        case "person":
            if entry.ext.occupations:
                parts.append(", ".join(entry.ext.occupations))
            if entry.ext.biography:
                parts.append(entry.ext.biography[:300])
        case "place":
            if entry.ext.place_type:
                parts.append(entry.ext.place_type)
            if entry.ext.address:
                parts.append(entry.ext.address)
        case "event":
            if entry.ext.started_at:
                parts.append(str(entry.ext.started_at.year))
            if entry.ext.location_text:
                parts.append(entry.ext.location_text)
        case "ai_conv":
            # userメッセージのみ（自分の思考）。assistantは含めない。
            messages = entry.ext.messages or []
            user_msgs = [m["content"] for m in messages if m["role"] == "user"]
            if user_msgs:
                parts.append(user_msgs[0])          # 最初の問い
                if len(user_msgs) > 1:
                    parts.append(user_msgs[-1])      # 最後の問い（会話の着地点）
        case "liked":
            if entry.ext.platform:
                parts.insert(0, entry.ext.platform)  # プラットフォームを先頭に
            if entry.ext.author_name:
                parts.append(entry.ext.author_name)
            if entry.ext.full_text:
                parts.append(entry.ext.full_text[:500])

    return "\n".join(filter(None, parts))[:2000]
```

#### 7.1.3 レート制限付きタスクキュー

Gemini API 無料枠（100 RPM）を超えないよう、Embedding生成は必ずキュー経由で行う。

```python
# services/task_queue.py

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Callable, Any
import time

@dataclass
class EmbeddingTask:
    entry_id: str
    callback: Callable

class RateLimitedQueue:
    """
    Gemini Embedding APIのレート制限（100 RPM）に対応したインメモリタスクキュー。

    【重要】インメモリのため WSL2 再起動・プロセス再起動でキューの内容は消える。
    フェーズ1 ではこれを許容する。
    フェーズ2 で embedding_job テーブル（後述）に移行し、再起動後もキューを復元できるようにする。
    """
    def __init__(self, rpm: int = 90):  # 余裕を持って90に設定
        self.rpm = rpm
        self.interval = 60.0 / rpm      # = 0.667秒/リクエスト
        self.queue: deque[EmbeddingTask] = deque()
        self.last_call_at: float = 0
        self._running = False

    async def enqueue(self, entry_id: str) -> None:
        self.queue.append(EmbeddingTask(entry_id=entry_id, callback=self._embed))
        if not self._running:
            asyncio.create_task(self._worker())

    async def _worker(self) -> None:
        self._running = True
        while self.queue:
            task = self.queue.popleft()
            now = time.monotonic()
            wait = self.interval - (now - self.last_call_at)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                await task.callback(task.entry_id)
            except Exception as e:
                # ロガーに記録してスキップ（キューを止めない）
                logger.error(f"Embedding failed for {task.entry_id}: {e}")
            self.last_call_at = time.monotonic()
        self._running = False

embedding_queue = RateLimitedQueue(rpm=int(settings.EMBEDDING_RATE_LIMIT_RPM))
```

**フェーズ2で移行する DB バックドキュー（`embedding_job` テーブル）**

```sql
-- フェーズ2で追加。再起動後も status='queued' のジョブを拾い直せる。
CREATE TABLE embedding_job (
    entry_id    UUID PRIMARY KEY REFERENCES entry(id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued', 'running', 'done', 'failed')),
    attempts    INT NOT NULL DEFAULT 0,
    error       TEXT,                           -- 失敗時のエラーメッセージ
    queued_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    done_at     TIMESTAMPTZ
);

-- embedding テーブルとの関係:
--   embedding_job.status = 'done' かつ embedding レコード存在 → 正常完了
--   embedding_job.status = 'failed'                           → 要確認

-- ライフサイクル:
--   done  レコード: 30日後に定期削除（cronでクリーンアップ）
--   failed レコード: 削除しない（デバッグ・手動再試行のため保持）

-- 起動時スタートアップ: status IN ('queued', 'running') を全件キューに再投入する処理を追加する
-- （'running' は前回の異常終了を意味するため再試行対象とする）
```

**フェーズ2 スタートアップ回復処理（実装例）**

```python
# services/embedding.py — アプリ起動時（lifespan）に呼び出す

MAX_ATTEMPTS = 3  # これを超えたら failed に変更

async def recover_embedding_jobs() -> None:
    """
    WSL2再起動・プロセス再起動後に未完了ジョブを復元する。
    - 'running' だったジョブ: 前回異常終了とみなし attempts をインクリメントして再投入
    - attempts >= MAX_ATTEMPTS のジョブ: 'failed' に変更してスキップ
    """
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT entry_id, status, attempts
                FROM embedding_job
                WHERE status IN ('queued', 'running')
                ORDER BY queued_at
            """)
        )
        rows = result.fetchall()

    for row in rows:
        entry_id, status, attempts = row

        # running だったジョブは異常終了扱い → attempts をカウントアップ
        new_attempts = attempts + 1 if status == 'running' else attempts

        if new_attempts >= MAX_ATTEMPTS:
            async with async_session() as session:
                await session.execute(
                    text("""
                        UPDATE embedding_job
                        SET status = 'failed', attempts = :attempts,
                            error = 'Max attempts exceeded on startup recovery'
                        WHERE entry_id = :id
                    """),
                    {"id": entry_id, "attempts": new_attempts}
                )
                await session.commit()
            logger.warning("embedding_job_failed_max_attempts",
                           entry_id=str(entry_id), attempts=new_attempts)
            continue

        # キューに再投入
        async with async_session() as session:
            await session.execute(
                text("""
                    UPDATE embedding_job
                    SET status = 'queued', attempts = :attempts
                    WHERE entry_id = :id
                """),
                {"id": entry_id, "attempts": new_attempts}
            )
            await session.commit()
        await embedding_queue.enqueue(str(entry_id))
        logger.info("embedding_job_recovered",
                    entry_id=str(entry_id), attempts=new_attempts)

    logger.info("embedding_recovery_complete", recovered=len(rows))


# main.py の lifespan に組み込む
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時
    await recover_embedding_jobs()
    yield
    # 終了時（必要なら後処理）

app = FastAPI(lifespan=lifespan)
```

#### 7.1.4 Embedding生成フロー

```python
# services/embedding.py

async def call_gemini_embedding(text: str) -> list[float]:
    """
    google-genai 新SDK でEmbeddingを生成する。
    旧: genai.embed_content()  →  新: client.models.embed_content()
    """
    from google import genai
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    result = await client.aio.models.embed_content(
        model=settings.EMBEDDING_MODEL,          # gemini-embedding-2-preview
        contents=text,
        config={"output_dimensionality": settings.EMBEDDING_DIMENSION},  # MRL截断用（3072のままなら省略可）
    )
    return result.embeddings[0].values

async def embed_entry(entry_id: UUID) -> None:
    entry = await get_entry_with_extension(entry_id)
    new_input_text = build_embedding_text(entry)

    # 差分チェック: テキストが変わっていなければAPIを呼ばない（コスト節約）
    existing = await get_embedding(entry_id)
    if existing and existing.input_text == new_input_text:
        logger.debug("embedding_skipped_no_change", entry_id=str(entry_id))
        return

    vector = await call_gemini_embedding(new_input_text)
    await upsert_embedding(entry_id, vector, new_input_text)

# Entry作成・更新時にキューへ追加（BackgroundTasks経由）
async def schedule_embedding(entry_id: UUID) -> None:
    await embedding_queue.enqueue(str(entry_id))
```

#### 7.1.5 再埋め込みトリガー

- entry の `title` または `content` 更新時
- 型別拡張テーブルのテキストフィールド更新時
- 手動: `POST /api/v1/entries/{id}/reembed`
- 一括: `POST /api/v1/entries/reembed-all`（キューに全件追加）

### 7.2 Search Engine

#### 7.2.1 検索モード

| モード | 説明 |
|--------|------|
| `semantic` | クエリをEmbedding化してコサイン類似度検索 |
| `fulltext` | pgroonga全文検索（日本語ネイティブ対応） |
| `hybrid` | Semantic + Fulltext のRRFスコア合算（デフォルト） |
| `graph` | connectionを再帰的に辿って関連entryを探索 |

#### 7.2.2 Hybrid Search（RRF実装）

```sql
-- Reciprocal Rank Fusion + Recency Boost
-- is_muted=TRUE のエントリーは検索対象から除外（削除せずランキングから降格）
WITH semantic AS (
    SELECT e.entry_id,
           ROW_NUMBER() OVER (ORDER BY e.vector <=> $1::vector) AS rank
    FROM embedding e
    JOIN entry en ON en.id = e.entry_id
    WHERE en.deleted_at IS NULL
      AND en.is_muted = FALSE      -- ミュート済みは除外
    ORDER BY e.vector <=> $1::vector
    LIMIT 50
),
fulltext AS (
    SELECT en.id AS entry_id,
           ROW_NUMBER() OVER (
               ORDER BY pgroonga_score(tableoid, ctid) DESC
           ) AS rank
    FROM entry en
    JOIN search_document sd ON sd.entry_id = en.id
    WHERE en.deleted_at IS NULL
      AND en.is_muted = FALSE      -- ミュート済みは除外
      AND sd.combined_text &@~ $2  -- pgroonga検索演算子
    ORDER BY pgroonga_score(tableoid, ctid) DESC
    LIMIT 50
)
SELECT
    COALESCE(s.entry_id, f.entry_id) AS entry_id,
    -- RRFスコア + recency boost（最近アクセスしたものを微小に優遇）
    -- recency_boost: 直近7日 +0.05、直近30日 +0.02、それ以外 0
    (COALESCE(1.0 / (60 + s.rank), 0) +
     COALESCE(1.0 / (60 + f.rank), 0)) AS rrf_score,
    CASE
        WHEN en.accessed_at > NOW() - INTERVAL '7 days'  THEN 0.05
        WHEN en.accessed_at > NOW() - INTERVAL '30 days' THEN 0.02
        ELSE 0
    END AS recency_boost
FROM semantic s
FULL OUTER JOIN fulltext f ON s.entry_id = f.entry_id
JOIN entry en ON en.id = COALESCE(s.entry_id, f.entry_id)
ORDER BY (rrf_score + recency_boost) DESC
LIMIT $3;
```


#### 7.2.3 検索パラメータ（Pydantic）

```python
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    mode: Literal["semantic", "fulltext", "hybrid", "graph"] = "hybrid"
    types: list[str] | None = None
    tags: list[str] | None = None
    topics: list[str] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    sort_by: Literal["relevance", "created_at", "updated_at", "accessed_at"] = "relevance"
    include_muted: bool = False        # TRUEのときis_muted=TRUEも含めて検索
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    include_deleted: bool = False      # 管理用
```

### 7.3 Connection Engine

#### 7.3.1 接続候補生成（`generate_connection_candidates`）

自動で `connection` を直接作成せず、`connection_candidate` に候補を積む（Section 5.5.2b参照）。  
ユーザーがUIで承認した時点で初めて `connection` になる。

```python
# config.py
class Settings(BaseSettings):
    AUTO_CONNECT_FETCH_TOP_N: int = 10
    AUTO_CONNECT_THRESHOLD: float = 0.88    # 実データ検証後に調整
    # ⚠️ デフォルトFALSE。フェーズ3の判断基準を満たしてからTRUEにする。
    AUTO_CONNECT_ENABLED: bool = False

# services/connection.py
async def generate_connection_candidates(entry_id: UUID) -> int:
    """
    類似エントリーを検索し connection_candidate に積む。
    直接 connection を作成しない。
    AUTO_CONNECT_ENABLED=False の場合は何もしない（フェーズ0〜2）。
    """
    if not settings.AUTO_CONNECT_ENABLED:
        return 0

    similar = await semantic_search_by_entry_id(
        entry_id=entry_id,
        limit=settings.AUTO_CONNECT_FETCH_TOP_N
    )
    created = 0
    for candidate in similar:
        if candidate.similarity < settings.AUTO_CONNECT_THRESHOLD:
            continue
        if candidate.entry_id == entry_id:
            continue
        try:
            async with async_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO connection_candidate
                            (entry_a_id, entry_b_id, similarity, suggested_type)
                        VALUES (:a, :b, :sim, 'related')
                        ON CONFLICT DO NOTHING
                    """),
                    {"a": str(entry_id), "b": str(candidate.entry_id),
                     "sim": candidate.similarity}
                )
                await session.commit()
            created += 1
        except Exception as e:
            logger.warning("candidate_insert_failed", error=str(e))
    return created
```

**候補有効化の判断基準（フェーズ3以降）:**

- タグ・トピックが50件以上整備されている
- 手動接続を20件以上作成し「有用な接続とは何か」の感覚がある
- 閾値を実データで検証済み（目安: 0.88以上）
- 同一タグを共有するエントリー間の候補を除外するフィルタを追加済み

#### 7.3.2 Knowledge Graph Walk

```python
async def get_knowledge_graph(
    entry_id: UUID,
    depth: int = 2,
    max_nodes: int = 100
) -> GraphData:
    """
    再帰CTEで depth 段階まで接続を辿る。
    max_nodes でノード数上限を設けてパフォーマンスを保護する。
    DB接続はすべて SQLAlchemy async session 経由で統一。
    """
    async with async_session() as session:
        rows = await session.execute(
            text("""
                WITH RECURSIVE graph AS (
                    SELECT entry_a_id AS src, entry_b_id AS dst,
                           relation_type, strength, is_auto, 1 AS depth
                    FROM connection
                    WHERE entry_a_id = :entry_id OR entry_b_id = :entry_id

                    UNION ALL

                    SELECT c.entry_a_id, c.entry_b_id,
                           c.relation_type, c.strength, c.is_auto, g.depth + 1
                    FROM connection c
                    JOIN graph g ON (c.entry_a_id = g.dst OR c.entry_b_id = g.dst)
                    WHERE g.depth < :depth
                )
                SELECT DISTINCT * FROM graph
                LIMIT :max_nodes
            """),
            {"entry_id": str(entry_id), "depth": depth, "max_nodes": max_nodes}
        )
    return build_graph_data(entry_id, rows.fetchall())
```

---

### 7.4 LLM Engine

KnOS では Embedding 以外に LLM を以下の用途で使用する。

| 用途 | 説明 |
|------|------|
| サマリー生成 | `entry.summary` の自動生成（インポート時・手動リクエスト時） |
| 構造化抽出 | スクレイプ HTML からメタデータ（著者・日付等）をJSON抽出 |
| OCR | `entry_media` の画像テキスト認識（Gemini Vision） |
| Obsidianインポート | wiki-link 解析・コンテンツ正規化 |
| クイズ生成 | Quiz衛星システムが `entry_definition` から選択肢を生成（フェーズ5） |

#### 7.4.1 モデル選択戦略

```python
# services/llm.py
# ⚠️ 旧 google-generativeai は2025年11月30日に非推奨化。
#    新 google-genai SDK を使用すること。
#    pip: google-genai   import: from google import genai

from google import genai
from google.genai import types

class LLMProvider(Protocol):
    async def generate(self, prompt: str, *, json_mode: bool = False) -> str: ...

class GeminiLLM:
    """
    プライマリ: gemini-2.5-flash（高速・高品質・無料枠あり）
    フォールバック: gemini-3-flash-preview（最新・無料枠あり）

    ⚠️ Gemini API Grounding 制約:
    Grounding（Google Search）と JSON 構造化出力の同時使用は不可。
    Grounding が必要なタスクは二段階処理で対応する（後述）。
    """
    def __init__(self):
        # google-genai 新SDK: Client を明示的に生成する
        self.client  = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.primary  = settings.LLM_PRIMARY_MODEL    # gemini-2.5-flash
        self.fallback = settings.LLM_FALLBACK_MODEL   # gemini-3-flash-preview

    async def _call(
        self, model: str, prompt: str, *,
        json_mode: bool = False, grounding: bool = False
    ) -> str:
        config = types.GenerateContentConfig()
        if json_mode:
            config.response_mime_type = "application/json"
        if grounding:
            config.tools = [types.Tool(google_search=types.GoogleSearch())]

        response = await self.client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        return response.text

    async def generate(self, prompt: str, *, json_mode: bool = False) -> str:
        for model in [self.primary, self.fallback]:
            try:
                return await self._call(model, prompt, json_mode=json_mode)
            except Exception as e:
                logger.warning("llm_model_failed", model=model, error=str(e))
        raise KnOSError("LLM_UNAVAILABLE", "All Gemini models failed", 503)

    async def generate_with_grounding(self, prompt: str) -> str:
        """
        Grounding（Google検索）が必要なタスク専用。
        JSON構造化出力との同時使用は不可のため、テキストのみ返す。
        構造化が必要な場合は generate_grounded_then_structure() を使うこと。
        """
        return await self._call(self.primary, prompt, grounding=True)

    async def generate_grounded_then_structure(
        self, search_prompt: str, structure_prompt_template: str
    ) -> dict:
        """
        Grounding制約の二段階回避パターン:
        Step1: Grounding有効で検索結果テキストを取得
        Step2: そのテキストをコンテキストとして渡し、JSON構造化出力を要求
        （Step2ではGroundingを使わないため制約に引っかからない）
        """
        search_result = await self.generate_with_grounding(search_prompt)
        structure_prompt = structure_prompt_template.format(
            search_context=search_result
        )
        raw = await self.generate(structure_prompt, json_mode=True)
        return json.loads(raw)


class OllamaLLM:
    """
    ローカルLLM（ollama）バックエンド。
    OLLAMA_BASE_URL が空の場合はインスタンス化しない。
    推奨モデル: qwopus3.5-9b-v3（HuggingFaceからGGUFを取得してModelfileで登録・Section 7.4.3参照）
    llama.cpp バックエンドも ollama 経由で使用可能。
    """
    def __init__(self):
        import ollama
        self.client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
        self.model  = settings.OLLAMA_MODEL

    async def generate(self, prompt: str, *, json_mode: bool = False) -> str:
        response = await self.client.generate(
            model=self.model,
            prompt=prompt,
            format="json" if json_mode else "",
        )
        return response.response


def get_llm() -> LLMProvider:
    """
    LLMプロバイダーを返す。
    OLLAMA_BASE_URL が設定されていれば OllamaLLM を優先する。
    （Gemini APIのレート制限を節約したい場合に有効）
    設定されていなければ GeminiLLM を使用。
    """
    if settings.OLLAMA_BASE_URL:
        return OllamaLLM()
    return GeminiLLM()
```

#### 7.4.2 Grounding 制約まとめ

| タスク | Grounding | JSON出力 | 対応方法 |
|--------|----------|---------|---------|
| サマリー生成 | 不要 | 不要 | `generate()` 直接 |
| 構造化メタデータ抽出 | 不要 | 必要 | `generate(json_mode=True)` |
| 外部情報を使った補完 | 必要 | 不要 | `generate_with_grounding()` |
| 外部情報を使った構造化 | 必要 | 必要 | `generate_grounded_then_structure()` |

#### 7.4.3 ollama / llama.cpp ローカル運用

WSL2上でollamaを動かすことでAPI コストゼロ・完全プライベートなLLMが使用できる。

**GPU動作条件（重要）**

| GPU | WSL2での動作 | 備考 |
|-----|------------|------|
| NVIDIA | ✅ 動作 | WindowsドライバーがCUDAパススルーを処理。WSL2内にLinuxドライバーをインストールしないこと |
| AMD | ❌ 非対応 | ROCmに必要な `/dev/kfd` がWSL2で公開されていない。素のLinuxかWindowsネイティブで運用 |
| CPU only | ✅ 動作 | GPU不要で動くが低速 |

```bash
# ollamaインストール（WSL2 Ubuntu 24.04 / NVIDIA GPU前提）
# Windows側のNVIDIAドライバーが v531以上であることを確認してから実行
curl -fsSL https://ollama.com/install.sh | sh

# 動作確認（NVIDIAの場合、GPUが検出されていることを確認）
ollama ps   # PROCESSOR列が "100% GPU" になっていることを確認
nvidia-smi  # ollamaプロセスがVRAMを確保していることを確認
```

**WSL2メモリ設定（`C:\Users\<username>\.wslconfig`）**

```ini
[wsl2]
networkingMode=mirrored   # ← これにより同WiFi内のAndroidからWSL2に直接アクセス可能
memory=16GB        # 9Bモデルに必要な分を確保（PCのRAMに合わせて調整）
swap=8GB
sparseVhd=true
```

**Qwopus3.5-9B-v3-GGUF の取り込み**

このモデルはollama公式registryにないため、HuggingFaceから手動でGGUFを取得してModelfileで登録する。

```bash
# 1. GGUFダウンロード（Q4_K_M推奨: 5.63GB・品質と速度のバランス）
#    VRAM 8GB以上 → Q6_K（7.36GB）、VRAM 12GB以上 → Q8_0（9.53GB）
wget https://huggingface.co/mradermacher/Qwopus3.5-9B-v3-GGUF/resolve/main/Qwopus3.5-9B-v3.Q4_K_M.gguf \
     -O ~/.ollama/models/Qwopus3.5-9B-v3.Q4_K_M.gguf

# 2. Modelfileを作成
cat > ~/Modelfile.qwopus << 'EOF'
FROM /root/.ollama/models/Qwopus3.5-9B-v3.Q4_K_M.gguf

# Qwen3.5のチャットテンプレートを指定
TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ range .Messages }}<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}<|im_start|>assistant
"""

PARAMETER num_ctx 32768      # 最大コンテキスト長
PARAMETER temperature 0.6
PARAMETER top_p 0.95
EOF

# 3. ollamaに登録
ollama create qwopus3.5-9b-v3 -f ~/Modelfile.qwopus

# 4. 動作確認
ollama run qwopus3.5-9b-v3 "こんにちは"
```

`.env` の `OLLAMA_MODEL` をこのモデル名に合わせる:

```env
OLLAMA_MODEL=qwopus3.5-9b-v3
```

モデルはWSL2のファイルシステム内（`~/.ollama/`）に置くこと。<br>
`/mnt/c/` 経由でアクセスするとファイルI/Oが3〜5倍遅くなる。

---

### 7.5 将来のBrain Layer — 設計指針（実装はフェーズ4以降）

このセクションは「今すぐ実装しない」が「将来なぜそうなるかを理解して設計する」ための指針。  
これを知っておくことで、フェーズ0〜3の設計が将来の拡張を妨げない形になる。

#### 7.5.1 時系列の重要性（Temporal Layer）

今の設計は **空間（Graph・類似度）** に強い。しかし人間の記憶は **時系列** に強く依存する。

```
「いつ見たか」「直前に何を見ていたか」「何週間後に再遭遇したか」
```

将来追加したくなる概念:

| 概念 | 説明 | 実装ヒント |
|------|------|-----------|
| Recency Score | 直近アクセスを微小にブースト | `accessed_at` 列（実装済み）+ 検索時の recency_boost |
| Session Memory | 同じ日に触れたエントリー同士を「文脈的接続」とみなす | `session_id` を entry に付与し、同session内を弱いconnectionとして扱う |
| Spaced Resurfacing | SRSとは別に「忘れた頃に再浮上させる」 | `last_resurfaced_at` + 確率的な resurfacing スケジューラ |
| Temporal Connection | 「同じ日に触れた」を接続の一種として扱う | `connection_type_def` に `co_accessed` を追加可能（Section 5.5.2b で拡張） |

**フェーズ0〜3でやること:** `accessed_at` を確実に更新する（エントリー閲覧時）。これがあれば将来のすべての時系列機能の基盤になる。

#### 7.5.2 情報寿命（Information Lifespan）

知識には寿命がある。設計がこれを無視すると「人生のゴミ箱」化する。

| 型 | 典型的な寿命 | 推奨対応 |
|----|------------|---------|
| `webpage`（ニュース系） | 数日〜数週間 | `is_muted=TRUE` に自動遷移（ドメイン・タグで判定） |
| `thought` | 長寿命（数年） | アーカイブなし |
| `definition` | 半永久 | アーカイブなし |
| `ai_conv` | 数週間〜数年（内容依存） | `is_useful` フラグで選別 |
| `liked` | 短〜中（気分で変わる） | 定期的に `is_muted` 候補として提示 |

将来追加したくなる機能:

```python
# 将来の実装イメージ（フェーズ4以降）
async def decay_old_entries():
    """
    一定期間アクセスがなく、muted候補のエントリーをサジェスト。
    自動mute は危険なのでサジェストのみ。ユーザーが判断する。
    """
    candidates = await session.execute(text("""
        SELECT id, type, title
        FROM entry
        WHERE accessed_at < NOW() - INTERVAL '6 months'
          AND created_at < NOW() - INTERVAL '3 months'
          AND is_muted = FALSE
          AND is_favorite = FALSE
          AND type IN ('webpage', 'liked', 'ai_conv')
        ORDER BY accessed_at ASC
        LIMIT 20
    """))
    # → UIで「整理しませんか？」として提示
```

#### 7.5.3 再利用コストの削減（Resurfacing & Relevance Engine）

保存コストは下げた。次の課題は **再利用コスト** 。

PKMで本当に重要なのは「保存」ではなく「今の思考と過去の知識がつながる」体験。  
これは Graph UIではなく **Relevance Engine** が担う。

将来の設計方向:

```
現在の思考（書きかけのthought）
    ↓ リアルタイムで類似search
関連する過去エントリー top 5 をサイドパネルに表示
= "今考えていることと昔考えたことがつながる"
```

実装の核心: `search_document.combined_text` が充実しているほど精度が上がる。  
フェーズ0〜3で `combined_text` を丁寧に育てることが、将来のRelevance Engineの品質を決める。

**今から設計に織り込むこと:**  
- `accessed_at` を閲覧のたびに更新する（必須）  
- `is_muted` でノイズを管理する（必須）  
- `search_document.combined_text` を型別戦略で構築する（必須）  
- SRSとは別の「受動的再浮上」の余地を残す（`last_resurfaced_at` カラムは将来追加）

---

## 8. API仕様

### 8.1 基本方針

| 項目 | 値 |
|------|-----|
| フレームワーク | FastAPI 0.136+ （Python 3.13） |
| 非同期 | asyncpg + SQLAlchemy 2.0 async |
| バリデーション | Pydantic v2 |
| 認証 | Cloudflare Access JWT（`Cf-Access-Jwt-Assertion`） |
| ベースURL | `https://api.knos.yourdomain.dev/api/v1` |
| レスポンス形式 | JSON（UTF-8） |
| APIバージョニング | URLパスに `/v1` を含める |

**DB接続方針（全コードで統一）:**  
すべてのDBアクセスは **SQLAlchemy async session** 経由で行う。生SQLが必要な箇所（Hybrid Search・Graph Walk等）は `sqlalchemy.text()` でラップし、asyncpg の生接続（`conn.fetch()`等）は使用しない。これにより接続プールとトランザクション管理が一元化される。

```python
# 正: SQLAlchemy text() を使用
from sqlalchemy import text
async with async_session() as session:
    result = await session.execute(text("SELECT ..."), {"param": value})

# 誤: asyncpg 生接続は使わない
rows = await conn.fetch("SELECT ...")  # ← 禁止
```

### 8.2 CORS設定

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "Cf-Access-Jwt-Assertion"],
)
```

開発環境では `ALLOWED_ORIGINS=http://localhost:3000` を設定する。

### 8.3 エラーレスポンス仕様

すべてのエラーは以下の統一フォーマットで返す。

```json
{
    "error": {
        "code": "ENTRY_NOT_FOUND",
        "message": "Entry with id '550e8400...' was not found.",
        "detail": null
    }
}
```

| HTTPステータス | エラーコード | 説明 |
|-------------|-------------|------|
| 400 | `INVALID_REQUEST` | バリデーションエラー |
| 400 | `INVALID_ENTRY_TYPE` | 存在しないentry_type |
| 401 | `UNAUTHORIZED` | 認証トークンなし・無効 |
| 404 | `ENTRY_NOT_FOUND` | 対象エントリーが存在しない |
| 404 | `CONNECTION_NOT_FOUND` | 対象接続が存在しない |
| 409 | `DUPLICATE_CONNECTION` | 同一の接続が既に存在する |
| 422 | `VALIDATION_ERROR` | 入力値の型・形式エラー（Pydantic） |
| 429 | `RATE_LIMITED` | Embedding APIレート制限中 |
| 500 | `INTERNAL_ERROR` | サーバー内部エラー |
| 503 | `EMBEDDING_UNAVAILABLE` | Embedding APIに接続できない |

```python
# errors.py
from fastapi import Request
from fastapi.responses import JSONResponse

class KnOSError(Exception):
    def __init__(self, code: str, message: str, status_code: int, detail=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail

async def knos_error_handler(request: Request, exc: KnOSError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "detail": exc.detail}}
    )
```

### 8.4 エンドポイント一覧

#### Entries

| Method | Path | 説明 |
|--------|------|------|
| GET | `/entries` | 一覧（ページネーション・フィルタ・ソート） |
| POST | `/entries` | 新規作成 |
| GET | `/entries/{id}` | 詳細（拡張テーブル・タグ・トピック含む）。**`accessed_at` を自動更新する** |
| PATCH | `/entries/{id}` | 部分更新 |
| DELETE | `/entries/{id}` | 論理削除（`deleted_at` をセット） |
| POST | `/entries/{id}/restore` | 論理削除の取り消し |
| PATCH | `/entries/{id}/mute` | `is_muted=TRUE` にする（ノイズ降格・削除なし） |
| PATCH | `/entries/{id}/unmute` | `is_muted=FALSE` にする |
| POST | `/entries/{id}/reembed` | Embedding再生成をキューに追加 |
| GET | `/entries/{id}/connections` | 接続エントリー一覧 |
| GET | `/entries/{id}/similar` | セマンティック類似エントリー上位N件 |

#### Search

| Method | Path | 説明 |
|--------|------|------|
| POST | `/search` | Hybrid/Semantic/Fulltext検索 |
| GET | `/search/suggest?q=` | タイトル・タグのオートコンプリート |

#### Graph

| Method | Path | 説明 |
|--------|------|------|
| GET | `/graph/{entry_id}?depth=2` | Knowledge Graphデータ（nodes + edges） |
| POST | `/connections` | 手動接続作成 |
| PATCH | `/connections/{id}` | 接続更新（note・strength） |
| DELETE | `/connections/{id}` | 接続削除 |
| GET | `/connection-candidates?status=pending` | 接続候補一覧（pending/approved/rejected） |
| POST | `/connection-candidates/{id}/approve` | 候補を承認→ `connection` 作成 |
| POST | `/connection-candidates/{id}/reject` | 候補を却下 |

#### Tags / Topics

| Method | Path | 説明 |
|--------|------|------|
| GET | `/tags` | タグ一覧（エントリー数付き） |
| POST | `/tags` | タグ作成 |
| DELETE | `/tags/{id}` | タグ削除（entry_tagも削除） |
| GET | `/topics` | トピック一覧（階層ツリー形式） |
| POST | `/topics` | トピック作成 |
| PATCH | `/topics/{id}` | トピック更新（親変更含む） |
| DELETE | `/topics/{id}` | トピック削除 |

#### Import

| Method | Path | 説明 |
|--------|------|------|
| POST | `/import/url` | URLからWebページ取り込み |
| POST | `/import/file` | ファイルアップロード取り込み |
| POST | `/import/notion` | Notionページ取り込み |
| POST | `/import/gdrive` | Google Driveファイル取り込み |
| POST | `/import/youtube-liked` | YouTube Liked一括取り込み（実装済・当面無効） |
| POST | `/import/x-archive` | XアーカイブJSONのインポート |
| GET | `/import/status/{job_id}` | インポートジョブの進捗確認 |

#### SRS

| Method | Path | 説明 |
|--------|------|------|
| GET | `/srs/due` | 本日復習すべきentryの一覧（`srs_current` ビュー経由） |
| POST | `/srs/{entry_id}/review` | 復習結果記録（SM-2計算） |
| GET | `/srs/stats` | 復習統計（日別・レベル別） |

#### Android Share Target のフロー

```
Android アプリ（Chrome・YouTube等）
    ↓ 「共有」 → KnOS を選択
manifest.json の "action": "/api/share" （Next.js フロントエンドのルート）
    ↓ POST application/x-www-form-urlencoded {title, text, url}
Next.js  app/api/share/route.ts  ← PWAマニフェストのactionと一致
    ↓ 内容を判定してバックエンドAPIへ転送
    ├── url あり  → POST api.knos.yourdomain.dev/api/v1/import/url
    └── textのみ → POST api.knos.yourdomain.dev/api/v1/entries  (type: thought)
```

```typescript
// frontend/app/api/share/route.ts
import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
    const data = await req.formData()
    const title = data.get('title')?.toString() ?? ''
    const text  = data.get('text')?.toString()  ?? ''
    const url   = data.get('url')?.toString()   ?? ''

    const API = process.env.BACKEND_URL  // e.g. http://localhost:8000

    if (url) {
        await fetch(`${API}/api/v1/import/url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, user_memo: text || undefined }),
        })
    } else {
        await fetch(`${API}/api/v1/entries`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'thought',
                title: title || text.slice(0, 50),
                content: text,
            }),
        })
    }
    // Share後はダッシュボードにリダイレクト
    return NextResponse.redirect(new URL('/', req.url))
}
```

`manifest.json` の `"action": "/api/share"` はNext.js側のルート。  
バックエンドの `/api/v1/share` エンドポイントは不要（フロントエンドのroute handlerで完結）。  
Section 8.4 の `POST /share` エンドポイントの記載は削除する。
```

### 8.5 レスポンス例

#### POST `/entries`

```json
// Request
{
    "type": "webpage",
    "title": "Attention Is All You Need",
    "source_url": "https://arxiv.org/abs/1706.03762",
    "content": "Transformer論文。Self-attentionの元祖。RNNを一切使わない設計が革新的。PositionalEncodingのあたり要再読。",
    "tags": ["transformer", "attention", "nlp"],
    "topics": ["機械学習/深層学習"],
    "extension": {
        "url": "https://arxiv.org/abs/1706.03762",
        "author": "Vaswani et al."
    }
}

// Response 201
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "webpage",
    "title": "Attention Is All You Need",
    "created_at": "2025-05-04T12:00:00Z",
    "embedding_status": "queued"
}
```

#### POST `/search`

```json
// Request
{
    "query": "Self-attentionとPositional Encodingの関係",
    "mode": "hybrid",
    "types": ["webpage", "definition", "thought"],
    "limit": 10
}

// Response 200
{
    "results": [
        {
            "entry_id": "550e8400-...",
            "type": "webpage",
            "title": "Attention Is All You Need",
            "score": 0.94,
            "snippet": "Self-attentionの元祖。RNNを一切使わない...",
            "tags": ["transformer", "attention"],
            "created_at": "2025-05-04T12:00:00Z"
        }
    ],
    "total": 47,
    "timing_ms": {
        "embedding": 42,
        "search": 18,
        "total": 63
    }
}
```

#### GET `/graph/{entry_id}`

```json
// Response 200
{
    "nodes": [
        {"id": "550e8400-...", "type": "webpage", "title": "Attention Is All You Need", "is_root": true},
        {"id": "661f9511-...", "type": "definition", "title": "Self-Attention", "is_root": false}
    ],
    "edges": [
        {
            "id": "...",
            "source": "550e8400-...",
            "target": "661f9511-...",
            "relation_type": "related",
            "strength": 0.91,
            "is_auto": true
        }
    ]
}
```

---

## 9. フロントエンド・UI仕様

### 9.1 技術スタック

| 項目 | 選択 |
|------|------|
| フレームワーク | Next.js 16（App Router） |
| スタイリング | Tailwind CSS |
| コンポーネント | shadcn/ui（Radix UIベース） |
| 状態管理 | Zustand |
| データフェッチ | TanStack Query v5 |
| グラフ可視化 | React Flow |
| PWA | next-pwa（Workbox） |
| アイコン | Lucide React |

### 9.2 UIデザイン原則

- **入力摩擦ゼロ:** クイック追加はどの画面からでも1タップで開く
- **情報の階層が一目でわかる:** タイプ別アイコン・カラーコードで型を視覚的に区別
- **モバイルファーストレイアウト:** すべての主要機能がAndroid Chromeで快適に使える
- **余白を活かす:** 情報密度より読みやすさを優先。ごちゃごちゃさせない
- **ダークモード対応:** デフォルトはシステム設定に従う

### 9.3 カラーシステム（型別）

| 型 | カラー |
|---|--------|
| webpage | Blue `#3B82F6` |
| thought | Purple `#8B5CF6` |
| book | Amber `#F59E0B` |
| video | Red `#EF4444` |
| document | Slate `#64748B` |
| definition | Green `#10B981` |
| person | Pink `#EC4899` |
| place | Teal `#14B8A6` |
| event | Orange `#F97316` |
| ai_conv | Indigo `#6366F1` |

### 9.4 主要画面設計

#### 9.4.1 ダッシュボード（`/`）

- **最近追加**（直近10件、型アイコン付きカード）
- **本日の復習**（SRSキュー件数と「始める」ボタン）
- **新着接続**（自動Connectionで新たにつながったペア、直近5件）
- **クイック追加フォーム**（URL入力欄 + メモ入力欄）

#### 9.4.2 検索画面（`/search`）

- 大きな検索バー（常に最上部・オートコンプリート付き）
- モード切替タブ（Hybrid / Semantic / Fulltext / Graph）
- フィルターパネル（型・タグ・トピック・日付範囲・折りたたみ可）
- 結果カード（スコアバー・スニペット・タグ・作成日）
- ソート切替（関連度 / 新しい順 / 古い順）
- 無限スクロール（TanStack Queryのカーソルページネーション）

#### 9.4.3 エントリー詳細（`/entries/[id]`）

- ヘッダー: 型バッジ・タイトル・ソースURL・お気に入りボタン
- コンテンツ: `entry.content`（Markdownレンダリング）
- 型別セクション（本: 読書ステータス・評価星、定義: 例文一覧、場所: 地図、AI会話: 会話ログ）
- **接続セクション:** 接続エントリー一覧（type別カラー・relation_typeラベル・手動追加UI）
- **類似セクション:** セマンティック類似上位5件（スコア付き）
- タグ・トピック編集（インライン編集）
- メタデータ（作成日・更新日・ソース）

#### 9.4.4 Knowledge Graph（`/graph`）

- React Flowによるインタラクティブグラフ
- ノード: 型別カラー・タイトル省略表示
- エッジ: relation_typeで線種を変える（related: 実線、references: 矢印、contradicts: 破線赤）
- クリック: 右サイドパネルでエントリー詳細プレビュー
- depthスライダー（1〜4）
- 起点エントリー検索（グラフ中央をどのエントリーにするか切替）
- フィット・ズームコントロール

#### 9.4.5 クイック追加（フローティング）

- すべての画面の右下に固定フローティングボタン
- タップで展開：「URLを追加」「メモを書く」の2択
- URLモード: URL入力 → スクレイプ進捗表示 → 完了通知
- メモモード: テキスト入力のみ → 即座に`thought`として保存

### 9.5 PWA設定（`public/manifest.json`）

```json
{
    "name": "Knowledge OS",
    "short_name": "KnOS",
    "description": "Personal Knowledge Management System",
    "display": "standalone",
    "start_url": "/",
    "background_color": "#0f172a",
    "theme_color": "#6366f1",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}
    ],
    "share_target": {
        "action": "/api/share",
        "method": "POST",
        "enctype": "application/x-www-form-urlencoded",
        "params": {
            "title": "title",
            "text": "text",
            "url": "url"
        }
    }
}
```

---

## 10. 外部連携・インポート仕様

### 10.1 インポートパイプライン共通フロー

```
入力ソース
    ↓
Adapter（ソース別変換）
    ↓
EntryCreateSchema（正規化・バリデーション）
    ↓
entry + extension テーブルへ保存
    ↓
Embedding生成タスクをキューへ追加
    ↓
自動Connection生成タスクをキューへ追加
```

### 10.2 Webスクレイパー（段階的フォールバック）

```python
# services/import_pipeline/url_scraper.py

async def fetch_webpage(url: str) -> ScrapedPage:
    """
    段階的フォールバック:
    段階1（Must）:  httpx + trafilatura — 軽量・高速。実際の80%はこれで十分。
    段階2（Should）: curl_cffi — TLSレベルでブラウザ偽装。Bot検知回避。
    段階3（Could）:  playwright — フルブラウザ・JS完全対応。
                    PLAYWRIGHT_ENABLED=true のときのみ有効。
                    Chromium依存・WSL2メモリ消費・メンテコスト高のためフェーズ2以降で追加。
    """
    scrapers: list = [scrape_with_httpx, scrape_with_curl_cffi]
    if settings.PLAYWRIGHT_ENABLED:
        scrapers.append(scrape_with_playwright)

    for scraper in scrapers:
        try:
            result = await scraper(url)
            if result.text and len(result.text) > 100:
                result.scraper_used = scraper.__name__
                return result
        except Exception as e:
            logger.warning(f"{scraper.__name__} failed for {url}: {e}")
            continue

    raise KnOSError("SCRAPE_FAILED", f"All scrapers failed for {url}", 422)


async def scrape_with_httpx(url: str) -> ScrapedPage:
    # ⚠️ trafilatura 2.0 breaking change:
    #   bare_extraction() が dict ではなく Document クラスを返すようになった。
    #   extract(output_format='json') はまだ動作するが、
    #   bare_extraction() を使う場合は result.text / result.title 等でアクセスする。
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (compatible; KnOS/1.0)"},
        follow_redirects=True,
        timeout=15.0
    ) as client:
        res = await client.get(url)
        res.raise_for_status()

    extracted = trafilatura.extract(
        res.text,
        include_comments=False,
        include_tables=True,
        with_metadata=True,
        output_format='json'
    )
    # OGP / <title> / <meta> もパース
    return build_scraped_page(url, res.text, extracted)


async def scrape_with_curl_cffi(url: str) -> ScrapedPage:
    from curl_cffi.requests import AsyncSession
    async with AsyncSession(impersonate="chrome120") as session:
        res = await session.get(url, timeout=15)
    extracted = trafilatura.extract(res.text, with_metadata=True, output_format='json')
    return build_scraped_page(url, res.text, extracted)


async def scrape_with_playwright(url: str) -> ScrapedPage:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        html = await page.content()
        await browser.close()
    extracted = trafilatura.extract(html, with_metadata=True, output_format='json')
    return build_scraped_page(url, html, extracted)
```

### 10.3 ファイルインポート

| ファイル形式 | テキスト抽出ライブラリ |
|------------|---------------------|
| PDF | `pdfplumber` |
| DOCX | `python-docx` |
| XLSX | `openpyxl`（シート名・セル内容） |
| PPTX | `python-pptx`（全スライドテキスト） |
| MD / TXT | そのまま |
| 画像（JPG/PNG） | Gemini Vision API |
| Notion Export（HTML/MD zip） | BeautifulSoup + Markdown変換 |
| Obsidian Export（MD zip） | Markdownパーサー + `[[wiki-link]]`変換 |

**Obsidian `[[wiki-link]]` 変換ルール:**

```python
# adapters/obsidian.py

import re

def convert_wiki_links(text: str, title_to_entry_id: dict[str, str]) -> tuple[str, list[dict]]:
    """
    [[ページ名]] を KnOS connection に変換する。
    title_to_entry_id: インポート済みentryのタイトル→IDのマップ

    変換結果:
    - マッチしたリンク → connection(references)として記録
    - マッチしないリンク → [ページ名](未解決)としてテキストに残す
    """
    connections = []
    pattern = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')

    def replace(m):
        target_title = m.group(1).strip()
        display_text = m.group(2) or target_title
        if target_title in title_to_entry_id:
            connections.append({
                "target_id": title_to_entry_id[target_title],
                "relation_type": "references"
            })
            return f"**{display_text}**"  # リンクをボールドに変換
        else:
            return f"[{display_text}](未解決: {target_title})"

    converted = pattern.sub(replace, text)
    return converted, connections
```

### 10.4 Notion インポート

```python
# adapters/notion.py
# Notion API バージョン: 2023-06-01

async def import_notion_page(page_id: str, api_key: str) -> EntryCreate:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2023-06-01"
    }
    # ページメタデータ取得
    page = await get(f"/v1/pages/{page_id}", headers)
    # ブロック内容取得（ページネーション対応）
    blocks = await get_all_blocks(page_id, headers)
    # ブロック → Markdown変換
    content_md = blocks_to_markdown(blocks)
    # プロパティ → metadata JSONB
    metadata = extract_notion_properties(page["properties"])

    return EntryCreate(
        type="document",
        title=extract_title(page),
        content=content_md,
        source_url=page["url"],
        metadata={"notion_id": page_id, **metadata},
        extension=DocumentExtension(
            doc_type="other",
            mime_type="text/notion",
            extracted_text=content_md
        )
    )
```

### 10.5 Google Drive インポート

```python
# adapters/google_drive.py
# Google Drive API v3

async def import_gdrive_file(file_id: str, credentials) -> EntryCreate:
    """
    ファイルをローカルにダウンロードせず、
    テキストのみエクスポートAPIで取得してextracted_textに保存する。
    """
    # メタデータ取得
    meta = await drive.files().get(fileId=file_id,
        fields="id,name,mimeType,modifiedTime,webViewLink,size").execute()

    # テキストエクスポート（GDocs/Sheets/Slides のみ）
    EXPORTABLE = {
        "application/vnd.google-apps.document": "text/plain",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.presentation": "text/plain",
    }
    extracted_text = None
    if meta["mimeType"] in EXPORTABLE:
        mime = EXPORTABLE[meta["mimeType"]]
        content = await drive.files().export(fileId=file_id, mimeType=mime).execute()
        extracted_text = content.decode("utf-8")

    return EntryCreate(
        type="document",
        title=meta["name"],
        source_url=meta["webViewLink"],
        extension=DocumentExtension(
            doc_type=mime_to_doc_type(meta["mimeType"]),
            gdrive_id=file_id,
            gdrive_url=meta["webViewLink"],
            gdrive_mime=meta["mimeType"],
            mime_type=meta["mimeType"],
            extracted_text=extracted_text
        )
    )
```

### 10.6 YouTube Liked インポート（実装済み・当面無効）

実装は完成させる。`YOUTUBE_API_KEY` 環境変数が空の場合はエンドポイント呼び出し時に `503 YOUTUBE_API_DISABLED` を返す。

```python
# adapters/youtube.py

async def import_youtube_liked(max_results: int = 200) -> list[EntryCreate]:
    if not settings.YOUTUBE_API_KEY:
        raise KnOSError("YOUTUBE_API_DISABLED",
                        "YouTube API is not configured.", 503)

    results = []
    page_token = None
    fetched = 0

    while fetched < max_results:
        params = {
            "part": "snippet",
            "playlistId": "LL",     # Liked List
            "maxResults": min(50, max_results - fetched),
            "key": settings.YOUTUBE_API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token

        data = await yt_api_get("/playlistItems", params)
        for item in data["items"]:
            results.append(youtube_item_to_entry(item))
        fetched += len(data["items"])
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return results
```

---

## 11. 衛星システム仕様

### 11.1 KnOS API との連携インターフェース

衛星システムはすべて以下のKnOS APIエンドポイントのみを使用する。APIトークンはCloudflare Access JWT。

| 衛星 | 使用するKnOSエンドポイント | 用途 |
|-----|--------------------------|------|
| Quiz | `GET /srs/due` | 本日の復習キュー取得 |
| Quiz | `POST /srs/{id}/review` | 復習結果を記録 |
| Quiz | `GET /entries?type=definition` | 全定義一覧取得 |
| Test | `POST /entries`（type: event） | テスト実施を出来事として記録 |
| Navi | `GET /entries?type=place` | 保存済み場所一覧取得 |
| Navi | `POST /entries`（type: place） | 新しい場所をKnOSに保存 |

### 11.2 Navi PWA（OSM/OTP/GTFS）

**リポジトリ:** `knowledge-os-navi/`  
**技術スタック:** Next.js PWA, Leaflet.js (react-leaflet), OpenTripPlanner API  

**機能:**
- 通学ルート最適化（OTP + GTFS-JPリアルタイム）
- お気に入りスポット管理（↔ KnOS `entry_place` と双方向同期）
- オフラインタイル対応（Leaflet + Service Worker）

### 11.3 Test Result System（GAS + Classroom）

**リポジトリ:** `knowledge-os-test/`  
**技術スタック:** Google Apps Script, Google Sheets, Classroom API  

**機能:**
- Google Classroomからの成績自動取得
- エビングハウス忘却曲線に基づく復習スケジュール
- Gemini API による記述問題AI評価
- テスト実施記録を `POST /entries`（type: event）でKnOSに送信（任意）

### 11.4 Quiz / Learning App

**リポジトリ:** `knowledge-os-quiz/`  
**技術スタック:** Next.js  

**機能:**
- `GET /srs/due` → 本日の定義カードを取得して出題
- フラッシュカード（表: term、裏: definition）
- SM-2グレード入力 → `POST /srs/{id}/review`
- 選択肢式クイズ（KnOSのdefinitionから自動生成）
- 学習統計グラフ

---

## 12. 開発フェーズ計画

> **最重要原則:** 知識OSの最大の敵は「完成前の疲弊」。各フェーズの**ゴールは次フェーズへの移行ではなく「毎日実際に使うこと」**。フェーズ0で毎日使えなければフェーズ1に進まない。

### フェーズ0 — 毎日使える最小版（目標: 3〜5日）

**ゴール:** 毎日実際に使う習慣を作る。技術的な完成度より「使い続けられること」が唯一の基準。

**禁止事項（全部後）:** Embedding・Vector Search・Graph・PostgreSQL・Docker・OAuth・PWA・Cloudflare・衛星システム・SRS・Google Drive・Notion・自動Connection・import pipeline・AI要約

```
使うもの: SQLite + FastAPI + (curlかシンプルなHTMLフォーム)
それだけ。
```

- [ ] WSL2で `uvicorn app.main:app --reload` で起動（設定ゼロ）
- [ ] テーブル: `entry`（id / title / content / type / created_at） + `tag` + `entry_tag` のみ
- [ ] エンドポイント: `POST /entries`・`GET /entries`・`GET /entries?q=` の3本のみ（SQL LIKE検索で十分）
- [ ] URLをペーストして保存できること（スクレイプ不要、URLだけ保存でよい）
- [ ] フロントエンド不要（curlかHTMLフォーム1枚で動作確認）
- [ ] **判定基準:** 3日連続で何かを記録した → 次フェーズへ

> Embeddingは「後でいつでも追加できる」。毎日使う習慣が先。

### フェーズ1 — PostgreSQL移行 + セマンティック検索（目標: 1〜2週間）

**ゴール:** フェーズ0のSQLiteデータをPostgreSQLに移行し、意味検索を追加する。

- [ ] DockerでPostgreSQL 17（groonga/pgroonga公式イメージ）を起動
- [ ] `entry` + `entry_webpage` + `entry_thought` + `embedding` + `search_document` テーブル作成
- [ ] FastAPI: CRUD + Hybrid Search（pgroonga + pgvector）
- [ ] Embedding Queue（インメモリ・レート制限付き）
- [ ] フェーズ0のSQLiteデータをPostgreSQLへ移行するスクリプト作成
- [ ] タグ・トピック管理
- [ ] エラーレスポンス統一・ロギング整備
- [ ] 日次バックアップ（age暗号化 + GitHub push）のcron設定
- [ ] **判定基準:** 検索が「使える」と感じること。毎日継続使用中

### フェーズ2 — モバイルアクセス + 全型対応（目標: +2〜3週間）

**ゴール:** Androidからも使えるようにする。全13型のデータが入るようにする。

- [ ] 最小フロントエンド（Next.js: ダッシュボード + 検索 + 詳細 + クイック追加）
- [ ] Cloudflare Tunnel + Access の設定（Android外出先アクセス用）
- [ ] Android ChromeからアクセスしてPWAとして追加
- [ ] Android Share Target実装
- [ ] WSL2 systemd + サービス自動起動設定
- [ ] 残り全型のテーブル・スキーマ（Alembicマイグレーション）
- [ ] Webスクレイパー段階的フォールバック完成（httpx+trafilatura必須・curl_cffi追加）
- [ ] ファイルインポート（PDF・DOCX）
- [ ] embedding_job テーブル移行（フェーズ1のインメモリキューを永続化）

### フェーズ3 — 接続・復習・UI完成（目標: +3〜4週間）

**ゴール:** 知識の「つながり」を発見できるようにする。ただしGraphは最小版から。

- [ ] **Knowledge Graph（最小版）:** Related entries list + Backlinks のみ。React Flowによる可視化は次フェーズ
- [ ] 手動Connection UI（2エントリー間に関係を定義）
- [ ] エントリー詳細画面（型別セクション・類似エントリー）
- [ ] SRS 定義カード復習UI
- [ ] ダークモード対応
- [ ] 自動Connection有効化（`AUTO_CONNECT_ENABLED=true`）— タグ整備・閾値検証後

### フェーズ4 — Knowledge Graph + 外部連携（目標: +4週間）

**ゴール:** Graphを本格実装し、既存ツールのデータを全部取り込む。

- [ ] Knowledge Graph（React Flow・インタラクティブ・depth指定）
- [ ] Notion API連携
- [ ] Google Drive API連携
- [ ] XアーカイブJSONインポート
- [ ] ObsidianエクスポートMarkdownインポート（wiki-link変換含む）
- [ ] YouTube Liked有効化（APIキー取得後）
- [ ] **長期運用検討:** mini PC + Linuxネイティブへの移行判断

### フェーズ5 — 衛星システム（目標: 別途計画）

- [ ] Navi PWA（OSM/OTP/GTFS）
- [ ] Test Result System（GAS）
- [ ] Quiz / Learning App

---

## 13. 非機能要件

### 13.1 パフォーマンス

| 項目 | 目標値 |
|------|--------|
| Hybrid検索（10万件未満） | < 500ms |
| Semantic検索のEmbedding生成 | < 2秒（API通信含む） |
| ページ初期表示 | < 2秒 |
| ファイルインポート（PDF 50ページ） | < 30秒 |
| Knowledge Graph（depth=2, 100ノード） | < 1秒 |

### 13.2 セキュリティ

- Cloudflare AccessによりGoogle OAuth認証を強制
- バックエンドは `127.0.0.1` にのみバインド（Tunnelを通じてのみアクセス可）
- `.env` はGit管理外（`.gitignore` に追加必須）
- APIキー・シークレットは環境変数のみで管理
- 開発環境（DEBUG=true）では認証スキップ可だが、本番では必ず有効化

### 13.3 拡張性

- **新しいentry_type:** `entry_type` テーブルへのINSERT + 拡張テーブル追加 + Adapterクラス追加のみ
- **新しい外部連携:** `adapters/` にAdapterクラスを追加するだけ
- **Embeddingモデル変更:** `services/embedding.py` の1クラスを差し替え（次元数変更時はDBマイグレーション必要）
- **検索エンジン追加:** `services/search.py` に新モードを追加

---

## 14. ロギング・モニタリング仕様

### 14.1 ロギング方針

- **ライブラリ:** Python標準 `logging` + `structlog`（構造化ログ）
- **出力先:** systemd journal（`journalctl -u knos-backend`）
- **フォーマット:** JSON形式（structlog）。`timestamp / level / event / request_id / ...`

### 14.2 ログレベル定義

| レベル | 用途 |
|--------|------|
| `DEBUG` | クエリ詳細・パラメータ（開発環境のみ） |
| `INFO` | リクエスト・レスポンス（正常系） |
| `WARNING` | スクレイプ失敗・レート制限接近・フォールバック発生 |
| `ERROR` | 例外・Embedding失敗・DB接続失敗 |
| `CRITICAL` | システム起動失敗・データ破損の恐れ |

### 14.3 リクエストロギングミドルウェア

```python
# middleware/logging_.py

import uuid, time
import structlog

logger = structlog.get_logger()

async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.monotonic()

    log = logger.bind(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    log.info("request_started")

    try:
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        log.info("request_finished",
                 status=response.status_code,
                 duration_ms=duration_ms)
        response.headers["X-Request-Id"] = request_id
        return response
    except Exception as e:
        log.error("request_failed", error=str(e), exc_info=True)
        raise
```

### 14.4 重要イベントのログ

```python
# 以下のイベントは必ずINFO以上でログを取る

logger.info("entry_created", entry_id=str(id), type=entry.type, title=entry.title)
logger.info("embedding_queued", entry_id=str(id), queue_size=len(queue))
logger.info("embedding_completed", entry_id=str(id), duration_ms=ms)
logger.warning("embedding_failed", entry_id=str(id), error=str(e), attempt=n)
logger.info("import_completed", source=source, entries_created=n, duration_ms=ms)
logger.warning("scraper_fallback", url=url, failed_scraper=name, next_scraper=next_name)
logger.info("connection_auto_created", entry_a=str(a), entry_b=str(b), strength=s)
logger.warning("rate_limit_approaching", remaining_rpm=n)
```

### 14.5 デバッグ手順（一人運用向け）

```bash
# バックエンドのリアルタイムログ
journalctl -u knos-backend -f

# 特定entry_idに関するログを抽出
journalctl -u knos-backend | grep "550e8400"

# エラーのみ抽出
journalctl -u knos-backend -p err -n 50

# Embeddingキューの詰まり確認
curl http://localhost:8000/api/v1/internal/queue-status

# DB接続確認
docker exec knos_db pg_isready -U knos

# 接続エントリー数確認
docker exec knos_db psql -U knos -c "SELECT COUNT(*) FROM connection;"
```

### 14.6 パフォーマンス計測

検索APIはレスポンスに `timing_ms` を含める（Section 8.5参照）。定期的に以下を確認する。

```sql
-- 遅いクエリの確認（pg_stat_statements が必要）
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- インデックス使用状況
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

---

*本設計書はPersonal Knowledge OS v10.0の実装指針である。*  
*フェーズ1着手前に通読し、疑義がある場合は実装前に解消すること。*  
*設計上の未決事項はゼロ。すべての判断が本書に記載されている。*s