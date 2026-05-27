// components/EntryDetail.tsx
"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { Star, StarOff, Trash2, Link as LinkIcon, BookOpen, Brain, RefreshCw } from "lucide-react"
import type { Entry } from "@/lib/api"
import { entriesApi, aiApi, srsApi } from "@/lib/api"
import { useStore } from "@/lib/store"
import { relativeTime, domain, TYPE_META, cn } from "@/lib/utils"
import { mutate } from "swr"

interface Props { entry: Entry }

export function EntryDetail({ entry }: Props) {
  const [busy, setBusy] = useState(false)
  const [summary, setSummary] = useState<string | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const { setSelectedEntry, bumpListRevision } = useStore()
  const meta = TYPE_META[entry.type]

  const toggleFavorite = async () => {
    setBusy(true)
    await entriesApi.update(entry.id, { is_favorite: !entry.is_favorite })
    bumpListRevision()
    mutate(["entry", entry.id])
    setBusy(false)
  }

  const handleDelete = async () => {
    if (!confirm(`「${entry.title}」を削除しますか?`)) return
    setBusy(true)
    await entriesApi.delete(entry.id)
    setSelectedEntry(null)
    bumpListRevision()
    setBusy(false)
  }

  const handleSummarize = async () => {
    setSummaryLoading(true)
    const res = await aiApi.summarize(entry.id).catch(() => null)
    setSummary(res?.summary || null)
    setSummaryLoading(false)
  }

  const handleEnrollSrs = async () => {
    await srsApi.enroll(entry.id).catch(() => null)
    alert(`「${entry.title}」をSRSに登録しました`)
  }

  const handleSuggestConnections = async () => {
    setBusy(true)
    const res = await aiApi.suggestConnections(entry.id).catch(() => null)
    if (res) alert(`${res.generated_candidates}件の接続候補を生成しました`)
    setBusy(false)
  }

  return (
    <div className="detail-panel">
      <div className="detail-header">
        {/* Actions */}
        <div className="detail-actions">
          <button
            type="button"
            className={cn("action-btn", entry.is_favorite && "active")}
            onClick={toggleFavorite}
            disabled={busy}
          >
            {entry.is_favorite ? <StarOff size={13} /> : <Star size={13} />}
            {entry.is_favorite ? "スター解除" : "スター"}
          </button>

          <button type="button" className="action-btn" onClick={handleEnrollSrs}>
            <BookOpen size={13} />
            SRS登録
          </button>

          <button type="button" className="action-btn" onClick={handleSuggestConnections} disabled={busy}>
            <RefreshCw size={13} />
            接続提案
          </button>

          <button
            type="button"
            className="action-btn"
            onClick={handleSummarize}
            disabled={summaryLoading}
          >
            <Brain size={13} />
            {summaryLoading ? "要約中…" : "要約"}
          </button>

          <button
            type="button"
            className="action-btn danger"
            onClick={handleDelete}
            disabled={busy}
          >
            <Trash2 size={13} />
            削除
          </button>
        </div>

        {/* Type & time */}
        <div className="detail-meta">
          <span className="entry-type-badge">{meta.icon} {meta.label}</span>
          <span>{relativeTime(entry.created_at)}</span>
          {entry.accessed_at && <span>最終閲覧: {relativeTime(entry.accessed_at)}</span>}
          {!entry.has_embedding && (
            <span style={{ color: "var(--text-subtle)", fontSize: 11 }}>Embedding待ち</span>
          )}
        </div>

        {/* Title */}
        <h1 className="detail-title">{entry.title || "(無題)"}</h1>

        {/* Source URL */}
        {entry.source_url && (
          <a
            href={entry.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="detail-source"
          >
            <LinkIcon size={12} />
            {domain(entry.source_url)}
          </a>
        )}

        {/* Tags */}
        {entry.tags.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 12 }}>
            {entry.tags.map(tag => (
              <span key={tag.id} className="tag-pill">#{tag.name}</span>
            ))}
          </div>
        )}
      </div>

      {/* AI Summary */}
      {summary && (
        <div style={{
          background: "var(--violet-dim)", border: "1px solid var(--violet)",
          borderRadius: "var(--radius)", padding: "12px 14px",
          fontSize: 13, lineHeight: 1.6, color: "var(--text)", marginBottom: 16,
        }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "var(--violet)", marginBottom: 6, letterSpacing: "0.06em" }}>
            🤖 AI SUMMARY
          </div>
          {summary}
        </div>
      )}

      {/* Content */}
      {entry.content ? (
        <div className="detail-content">{entry.content}</div>
      ) : (
        <p style={{ color: "var(--text-subtle)", fontSize: 13 }}>コンテンツなし</p>
      )}
    </div>
  )
}
