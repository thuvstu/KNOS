// components/PostCard.tsx
'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Heart, ExternalLink } from 'lucide-react'
import type { Post } from '@/lib/types'
import { POST_TYPE_LABELS, POST_TYPE_COLORS } from '@/lib/types'
import { formatRelativeTime, stripMarkdown, truncate, extractDomain, cn } from '@/lib/utils'
import { getSupabaseBrowserClient } from '@/lib/supabase'

interface PostCardProps {
  post: Post
  onTagClick?: (tag: string) => void
}

export function PostCard({ post, onTagClick }: PostCardProps) {
  const [likes, setLikes] = useState(post.like_count)
  const [liked, setLiked] = useState(false)
  const [liking, setLiking] = useState(false)

  const authorName = post.profiles?.display_name || post.anon_name || 'Anonymous'
  const preview = truncate(stripMarkdown(post.content || post.blocks_text || ''), 160)

  const handleLike = async () => {
    if (liking) return
    setLiking(true)

    const supabase = getSupabaseBrowserClient()
    const { data: { session } } = await supabase.auth.getSession()

    let userId = session?.user?.id
    if (!userId) {
      const { data } = await supabase.auth.signInAnonymously()
      userId = data.user?.id
    }

    if (!userId) { setLiking(false); return }

    // 楽観的更新
    const newLiked = !liked
    setLiked(newLiked)
    setLikes((n) => n + (newLiked ? 1 : -1))

    if (newLiked) {
      const { error } = await supabase.from('likes').insert({ post_id: post.id, user_id: userId })
      if (error) { setLiked(false); setLikes((n) => n - 1) }
    } else {
      const { error } = await supabase.from('likes').delete().eq('post_id', post.id).eq('user_id', userId)
      if (error) { setLiked(true); setLikes((n) => n + 1) }
    }

    setLiking(false)
  }

  return (
    <article className="post-card">
      <div className="post-card-header">
        <div className="post-card-meta">
          <span className={cn('post-type-badge', POST_TYPE_COLORS[post.type])}>
            {POST_TYPE_LABELS[post.type]}
          </span>
          <time className="post-date">{formatRelativeTime(post.created_at)}</time>
        </div>
        <span className="post-author">{authorName}</span>
      </div>

      <Link href={`/post/${post.id}`} className="post-card-title">
        {post.title}
      </Link>

      {post.type === 'link' && post.source_url && (
        <a
          href={post.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="post-source-url"
        >
          <ExternalLink size={12} />
          {extractDomain(post.source_url)}
        </a>
      )}

      {preview && <p className="post-preview">{preview}</p>}

      <div className="post-card-footer">
        <div className="post-tags">
          {post.tags.slice(0, 5).map((tag) => (
            <button
              key={tag}
              type="button"
              className="tag-chip"
              onClick={() => onTagClick?.(tag)}
            >
              #{tag}
            </button>
          ))}
          {post.tags.length > 5 && (
            <span className="tag-more">+{post.tags.length - 5}</span>
          )}
        </div>

        <button
          type="button"
          className={cn('like-btn', liked && 'liked')}
          onClick={handleLike}
          disabled={liking}
        >
          <Heart size={14} fill={liked ? 'currentColor' : 'none'} />
          <span>{likes}</span>
        </button>
      </div>
    </article>
  )
}
