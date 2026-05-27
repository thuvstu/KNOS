// components/QuickAdd.tsx
"use client"
import { useState, useEffect, useRef } from "react"
import { X } from "lucide-react"
import { entriesApi, importApi } from "@/lib/api"
import type { EntryType } from "@/lib/api"
import { useStore } from "@/lib/store"
import { TYPE_META, ALL_TYPES, cn } from "@/lib/utils"

export function QuickAdd() {
  const { quickAddOpen, setQuickAddOpen, bumpListRevision } = useStore()
  const [type, setType]     = useState<EntryType>("thought")
  const [title, setTitle]   = useState("")
  const [content, setContent] = useState("")
  const [url, setUrl]       = useState("")
  const [tags, setTags]     = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState("")
  const titleRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (quickAddOpen) {
      setTitle(""); setContent(""); setUrl(""); setTags(""); setError("")
      setTimeout(() => titleRef.current?.focus(), 80)
    }
  }, [quickAddOpen])

  // ⌘N / Ctrl+N でトグル
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "n") {
        e.preventDefault()
        setQuickAddOpen(!quickAddOpen)
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [quickAddOpen])

  if (!quickAddOpen) return null

  const submit = async () => {
    if (!title.trim() && !url.trim()) { setError("タイトルまたはURLを入力してください"); return }
    setLoading(true); setError("")

    try {
      const parsedTags = tags.split(",").map(t => t.trim()).filter(Boolean)

      // URL貼り付け → 自動スクレイプ
      if ((type === "webpage") && url.trim()) {
        await importApi.importUrl(url.trim(), parsedTags)
      } else {
        await entriesApi.create({
          type,
          title: title.trim() || url.trim(),
          content: content.trim(),
          source_url: url.trim(),
          tags: parsedTags,
        })
      }

      bumpListRevision()
      setQuickAddOpen(false)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "エラーが発生しました")
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") setQuickAddOpen(false)
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") submit()
  }

  return (
    <div className="modal-overlay" onClick={() => setQuickAddOpen(false)}>
      <div className="modal" onClick={e => e.stopPropagation()} onKeyDown={handleKey}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <h2 className="modal-title" style={{ margin: 0 }}>新規エントリー</h2>
          <button
            type="button"
            style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
            onClick={() => setQuickAddOpen(false)}
          >
            <X size={16} />
          </button>
        </div>

        {/* Type selector */}
        <div className="form-group">
          <label className="form-label">タイプ</label>
          <div className="type-grid">
            {ALL_TYPES.map(t => {
              const meta = TYPE_META[t]
              return (
                <button
                  key={t}
                  type="button"
                  className={cn("type-btn", type === t && "active")}
                  onClick={() => setType(t)}
                >
                  <span style={{ fontSize: 16 }}>{meta.icon}</span>
                  <span>{meta.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Title */}
        <div className="form-group">
          <label className="form-label">タイトル</label>
          <input
            ref={titleRef}
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="エントリーのタイトル"
            className="form-input"
          />
        </div>

        {/* URL */}
        {(type === "webpage" || type === "video" || type === "liked") && (
          <div className="form-group">
            <label className="form-label">URL {type === "webpage" && "(自動スクレイプ)"}</label>
            <input
              type="url"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://..."
              className="form-input"
            />
          </div>
        )}

        {/* Content */}
        <div className="form-group">
          <label className="form-label">本文</label>
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            placeholder="メモ、引用、考えなど…"
            className="form-textarea"
            rows={4}
          />
        </div>

        {/* Tags */}
        <div className="form-group">
          <label className="form-label">タグ (カンマ区切り)</label>
          <input
            type="text"
            value={tags}
            onChange={e => setTags(e.target.value)}
            placeholder="ai, paper, todo"
            className="form-input"
          />
        </div>

        {error && <p className="error-text">{error}</p>}

        <button type="button" className="btn-primary" onClick={submit} disabled={loading}>
          {loading ? "追加中…" : "追加 (⌘↵)"}
        </button>
      </div>
    </div>
  )
}
