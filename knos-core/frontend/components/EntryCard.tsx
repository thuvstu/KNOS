// components/EntryCard.tsx
"use client"
import type { Entry } from "@/lib/api"
import { useStore } from "@/lib/store"
import { relativeTime, truncate, TYPE_META, cn } from "@/lib/utils"

export function EntryCard({ entry }: { entry: Entry }) {
  const { selectedEntry, setSelectedEntry, setActiveTag } = useStore()
  const selected = selectedEntry?.id === entry.id
  const meta = TYPE_META[entry.type]

  return (
    <article
      className={cn("entry-card", selected && "selected")}
      onClick={() => setSelectedEntry(selected ? null : entry)}
    >
      <div className="entry-card-header">
        <span className="entry-type-badge">
          {meta.icon} {meta.label}
        </span>
        {entry.is_favorite && <span style={{ color: "var(--accent)", fontSize: 12 }}>★</span>}
        <span className="entry-time">{relativeTime(entry.created_at)}</span>
      </div>

      <div className="entry-title">{entry.title || "(無題)"}</div>

      {entry.content && (
        <div className="entry-preview">{truncate(entry.content, 120)}</div>
      )}

      {(entry.tags.length > 0 || entry.has_embedding) && (
        <div className="entry-footer">
          {entry.tags.slice(0, 4).map(tag => (
            <button
              key={tag.id}
              type="button"
              className="tag-pill"
              onClick={e => { e.stopPropagation(); setActiveTag(tag.name) }}
            >
              #{tag.name}
            </button>
          ))}
          {entry.has_embedding && (
            <span style={{ fontSize: 10, color: "var(--text-subtle)", marginLeft: "auto" }} title="Embedding済み">
              ⚡
            </span>
          )}
          {entry.is_favorite && <span className="fav-dot" />}
        </div>
      )}
    </article>
  )
}
