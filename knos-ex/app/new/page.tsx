// app/new/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import type { JSONContent } from '@tiptap/react'
import { getSupabaseBrowserClient } from '@/lib/supabase'
import type { PostType } from '@/lib/types'
import { POST_TYPE_LABELS } from '@/lib/types'
import { extractText, extractBlockTags, collectAllBlockTags } from '@/lib/editor/blockUtils'
import { cn } from '@/lib/utils'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'

// Dynamic import to avoid SSR issues with Tiptap
const RichEditor = dynamic(() => import('@/components/editor/RichEditor').then(m => ({ default: m.RichEditor })), {
  ssr: false,
  loading: () => <div className="loading" style={{ minHeight: 200 }}>エディター読み込み中…</div>
})

const POST_TYPES: PostType[] = ['article', 'note', 'link', 'knowledge', 'question']

export default function NewPostPage() {
  const router = useRouter()
  const [type, setType] = useState<PostType>('note')
  const [title, setTitle] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [blocks, setBlocks] = useState<JSONContent | null>(null)
  const [tags, setTags] = useState('')
  const [anonName, setAnonName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!title.trim()) { setError('タイトルを入力してください'); return }
    if (type === 'link' && !sourceUrl.trim()) { setError('URLを入力してください'); return }

    setSubmitting(true)
    setError('')

    const supabase = getSupabaseBrowserClient()

    // 匿名ログイン（未ログインの場合）
    let userId: string | null = null
    const { data: { session } } = await supabase.auth.getSession()
    if (session?.user) {
      userId = session.user.id
    } else {
      const { data } = await supabase.auth.signInAnonymously()
      userId = data.user?.id || null
    }

    if (!userId) { setError('認証に失敗しました'); setSubmitting(false); return }

    // テキスト抽出
    const content = blocks ? extractText(blocks) : ''
    const blocksText = content
    const blockTagEntries = blocks ? extractBlockTags(blocks) : []
    const blockTagList = blocks ? collectAllBlockTags(blocks) : []

    // 投稿タグをパース
    const postTags = tags.split(',').map(t => t.trim()).filter(Boolean)
    // ブロックタグを投稿タグにマージ
    const allTags = [...new Set([...postTags, ...blockTagList])]

    const { data: post, error: insertError } = await supabase
      .from('posts')
      .insert({
        type,
        title: title.trim(),
        content,
        blocks: blocks || undefined,
        blocks_text: blocksText || undefined,
        source_url: sourceUrl.trim(),
        user_id: userId,
        anon_name: anonName.trim() || 'Anonymous',
        tags: allTags,
        is_published: true,
      })
      .select()
      .single()

    if (insertError) {
      setError(insertError.message)
      setSubmitting(false)
      return
    }

    // ブロックタグを同期
    if (blockTagEntries.length > 0 && post) {
      await supabase.rpc('sync_block_tags', {
        p_post_id: post.id,
        p_block_tags: blockTagEntries,
      })
    }

    router.push(`/post/${post.id}`)
  }

  return (
    <div className="page-container">
      <Link href="/" className="back-link">
        <ArrowLeft size={14} /> フィードへ戻る
      </Link>

      <div className="new-post-form">
        <h1 style={{ fontSize: 22, fontWeight: 900, marginBottom: 24, letterSpacing: '-0.03em' }}>
          新しい投稿
        </h1>

        {/* 投稿タイプ */}
        <div className="form-section">
          <label className="form-label">投稿タイプ</label>
          <div className="type-selector">
            {POST_TYPES.map(t => (
              <button
                key={t}
                type="button"
                className={cn('type-selector-btn', type === t && 'active')}
                onClick={() => setType(t)}
              >
                {POST_TYPE_LABELS[t]}
              </button>
            ))}
          </div>
        </div>

        {/* タイトル */}
        <div className="form-section">
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="タイトルを入力..."
            className="form-title-input"
            maxLength={200}
          />
        </div>

        {/* URL (link タイプ) */}
        {(type === 'link' || sourceUrl) && (
          <div className="form-section">
            <label className="form-label">URL</label>
            <input
              type="url"
              value={sourceUrl}
              onChange={e => setSourceUrl(e.target.value)}
              placeholder="https://..."
              className="form-input"
            />
          </div>
        )}

        {/* エディター */}
        <div className="form-section">
          <label className="form-label">本文</label>
          <RichEditor
            onChange={setBlocks}
            placeholder="ここに内容を書いてください… /でブロックを挿入"
            minHeight="320px"
          />
        </div>

        {/* タグ */}
        <div className="form-section">
          <label className="form-label">タグ <span style={{ fontWeight: 400, color: 'var(--text-subtle)' }}>(カンマ区切り)</span></label>
          <input
            type="text"
            value={tags}
            onChange={e => setTags(e.target.value)}
            placeholder="javascript, react, tips"
            className="form-input"
          />
        </div>

        {/* 表示名 */}
        <div className="form-section">
          <label className="form-label">表示名 <span style={{ fontWeight: 400, color: 'var(--text-subtle)' }}>(省略可)</span></label>
          <input
            type="text"
            value={anonName}
            onChange={e => setAnonName(e.target.value)}
            placeholder="Anonymous"
            className="form-input"
            maxLength={50}
          />
        </div>

        {error && <p className="error-msg">{error}</p>}

        <button
          type="button"
          className="submit-btn"
          onClick={handleSubmit}
          disabled={submitting}
        >
          {submitting ? '投稿中…' : '投稿する'}
        </button>
      </div>
    </div>
  )
}
