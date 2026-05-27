// components/FeedFilter.tsx
'use client'

import { useState, useEffect } from 'react'
import { Search, X } from 'lucide-react'
import type { PostType } from '@/lib/types'
import { POST_TYPE_LABELS } from '@/lib/types'
import { getSupabaseBrowserClient } from '@/lib/supabase'
import { cn } from '@/lib/utils'

interface FeedFilterProps {
  onFilterChange: (filters: {
    query: string
    type: PostType | ''
    tag: string
  }) => void
  initialTag?: string
}

const POST_TYPES: Array<{ value: PostType | ''; label: string }> = [
  { value: '', label: 'すべて' },
  { value: 'article', label: '記事' },
  { value: 'note', label: 'メモ' },
  { value: 'link', label: 'リンク' },
  { value: 'knowledge', label: '知識' },
  { value: 'question', label: '質問' },
]

export function FeedFilter({ onFilterChange, initialTag = '' }: FeedFilterProps) {
  const [query, setQuery] = useState('')
  const [type, setType] = useState<PostType | ''>('')
  const [tag, setTag] = useState(initialTag)
  const [popularTags, setPopularTags] = useState<Array<{ tag: string; post_count: number }>>([])

  useEffect(() => {
    const supabase = getSupabaseBrowserClient()
    supabase.from('tag_counts').select('tag, post_count').limit(12).then(({ data }) => {
      if (data) setPopularTags(data as Array<{ tag: string; post_count: number }>)
    })
  }, [])

  useEffect(() => {
    onFilterChange({ query, type, tag })
  }, [query, type, tag])

  const clearAll = () => {
    setQuery('')
    setType('')
    setTag('')
  }

  const hasFilter = query || type || tag

  return (
    <div className="feed-filter">
      {/* 検索バー */}
      <div className="search-bar">
        <Search size={16} className="search-icon" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="キーワード検索..."
          className="search-input"
        />
        {query && (
          <button type="button" onClick={() => setQuery('')} className="search-clear">
            <X size={14} />
          </button>
        )}
      </div>

      {/* タイプフィルター */}
      <div className="type-filter">
        {POST_TYPES.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => setType(value)}
            className={cn('type-chip', type === value && 'type-chip-active')}
          >
            {label}
          </button>
        ))}
      </div>

      {/* タグフィルター */}
      {popularTags.length > 0 && (
        <div className="popular-tags">
          <span className="popular-tags-label">人気タグ:</span>
          <div className="popular-tags-list">
            {popularTags.map(({ tag: t, post_count }) => (
              <button
                key={t}
                type="button"
                onClick={() => setTag(tag === t ? '' : t)}
                className={cn('tag-chip', tag === t && 'tag-chip-active')}
              >
                #{t}
                <span className="tag-count">{post_count}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* アクティブなタグフィルター表示 */}
      {tag && (
        <div className="active-tag-filter">
          <span className="text-sm text-gray-600 dark:text-gray-400">フィルター:</span>
          <span className="active-tag-chip">
            #{tag}
            <button type="button" onClick={() => setTag('')}><X size={12} /></button>
          </span>
        </div>
      )}

      {/* クリアボタン */}
      {hasFilter && (
        <button type="button" onClick={clearAll} className="filter-clear-btn">
          フィルターをクリア
        </button>
      )}
    </div>
  )
}
