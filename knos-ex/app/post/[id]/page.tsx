// app/post/[id]/page.tsx
import { getSupabaseServerClient } from '@/lib/supabase'
import type { Post } from '@/lib/types'
import { POST_TYPE_LABELS, POST_TYPE_COLORS } from '@/lib/types'
import { formatRelativeTime, extractDomain, cn } from '@/lib/utils'
import { ArrowLeft, Heart, ExternalLink } from 'lucide-react'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import { notFound } from 'next/navigation'
import type { JSONContent } from '@tiptap/react'

const BlockRenderer = dynamic(
  () => import('@/components/editor/BlockRenderer').then(m => ({ default: m.BlockRenderer })),
  { ssr: false, loading: () => <div className="loading">コンテンツ読み込み中…</div> }
)

interface Props {
  params: Promise<{ id: string }>
}

export default async function PostDetailPage({ params }: Props) {
  const { id } = await params
  const supabase = getSupabaseServerClient()

  const { data, error } = await supabase
    .from('posts')
    .select('*, profiles(display_name, avatar_url, is_anon)')
    .eq('id', id)
    .eq('is_published', true)
    .single()

  if (error || !data) notFound()

  const post = data as Post
  const authorName = post.profiles?.display_name || post.anon_name || 'Anonymous'

  return (
    <div className="page-container">
      <Link href="/" className="back-link">
        <ArrowLeft size={14} /> フィードへ戻る
      </Link>

      <article className="post-detail">
        <header className="post-detail-header">
          <div className="post-detail-meta">
            <span className={cn('post-type-badge', POST_TYPE_COLORS[post.type])}>
              {POST_TYPE_LABELS[post.type]}
            </span>
            <time>{formatRelativeTime(post.created_at)}</time>
            <span>by {authorName}</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <Heart size={13} fill="none" /> {post.like_count}
            </span>
          </div>

          <h1 className="post-detail-title">{post.title}</h1>

          {post.type === 'link' && post.source_url && (
            <a
              href={post.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="post-source-url"
              style={{ fontSize: 14, marginBottom: 16, display: 'inline-flex' }}
            >
              <ExternalLink size={14} />
              {extractDomain(post.source_url)}
            </a>
          )}
        </header>

        {/* コンテンツ */}
        {post.blocks ? (
          <BlockRenderer blocks={post.blocks as JSONContent} />
        ) : post.content ? (
          <div className="prose prose-slate dark:prose-invert max-w-none">
            <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>{post.content}</p>
          </div>
        ) : null}

        {/* タグ */}
        {post.tags.length > 0 && (
          <div style={{ marginTop: 32, paddingTop: 20, borderTop: '1px solid var(--border)' }}>
            <div className="post-tags">
              {post.tags.map((tag) => (
                <Link key={tag} href={`/?tag=${tag}`} className="tag-chip">
                  #{tag}
                </Link>
              ))}
            </div>
          </div>
        )}
      </article>
    </div>
  )
}
