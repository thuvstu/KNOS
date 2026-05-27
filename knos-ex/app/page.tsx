// app/page.tsx
'use client'

import { useState, useEffect, useCallback } from 'react'
import { getSupabaseBrowserClient } from '@/lib/supabase'
import type { Post, PostType } from '@/lib/types'
import { PostCard } from '@/components/PostCard'
import { FeedFilter } from '@/components/FeedFilter'
import { useSearchParams } from 'next/navigation'

export default function FeedPage() {
  const searchParams = useSearchParams()
  const initialTag = searchParams.get('tag') || ''

  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ query: '', type: '' as PostType | '', tag: initialTag })

  const fetchPosts = useCallback(async () => {
    setLoading(true)
    const supabase = getSupabaseBrowserClient()

    let q = supabase
      .from('posts')
      .select('*, profiles(display_name, avatar_url, is_anon)')
      .eq('is_published', true)
      .order('created_at', { ascending: false })
      .limit(30)

    if (filters.query) {
      q = q.or(
        `title.ilike.%${filters.query}%,content.ilike.%${filters.query}%,blocks_text.ilike.%${filters.query}%`
      )
    }
    if (filters.type) q = q.eq('type', filters.type)
    if (filters.tag) q = q.contains('tags', [filters.tag])

    const { data, error } = await q
    if (!error && data) setPosts(data as Post[])
    setLoading(false)
  }, [filters])

  useEffect(() => { fetchPosts() }, [fetchPosts])

  return (
    <div className="page-container">
      <div className="hero">
        <h1 className="hero-title">KnOS EX</h1>
        <p className="hero-sub">知識を共有しよう — 記事・メモ・リンク・質問、なんでも</p>
      </div>

      <FeedFilter onFilterChange={setFilters} initialTag={initialTag} />

      {loading ? (
        <div className="loading">読み込み中…</div>
      ) : posts.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📭</div>
          <p className="empty-state-text">投稿が見つかりません</p>
        </div>
      ) : (
        <div className="post-list">
          {posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              onTagClick={(tag) => setFilters((f) => ({ ...f, tag }))}
            />
          ))}
        </div>
      )}
    </div>
  )
}
