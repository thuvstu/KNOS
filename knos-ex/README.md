# KnOS EX

誰でも・ログイン不要で・どんなコンテンツでも投稿できる、ブロック単位の自由度を持つ知識共有プラットフォーム。

## 特徴

- **匿名投稿 OR OAuth** — 登録不要でその場で投稿可能
- **ブロックベースエディター** — Tiptap + スラッシュコマンド19種
- **KaTeX数式** — インライン `$...$` / ブロック `$$...$$`
- **コードブロック** — 10言語HL + ワンクリックコピー
- **動画埋め込み** — YouTube / Vimeo
- **Callout** — info / tip / warning / danger
- **ブロック単位タグ** — 各ブロックにタグを付けて検索可能

## セットアップ

```bash
cp .env.example .env.local
# .env.local を編集してSupabase情報を入力

npm install
npm run dev
```

## Supabase設定

1. supabase.com で新規プロジェクト作成
2. SQL Editorで順番に実行:
   - `supabase/migrations/001_init.sql`
   - `supabase/migrations/002_blocks.sql`
3. Authentication → Providers → Google / GitHub を設定

## デプロイ (Vercel)

```bash
vercel
# 環境変数を Vercel Dashboard で設定
```
