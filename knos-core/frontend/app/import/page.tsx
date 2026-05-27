// app/import/page.tsx
"use client"
import { useState, useRef } from "react"
import { SWRConfig } from "swr"
import { Topbar } from "@/components/Topbar"
import { Sidebar } from "@/components/Sidebar"
import { QuickAdd } from "@/components/QuickAdd"
import { importApi } from "@/lib/api"
import { useStore } from "@/lib/store"
import { Globe, FileText, Archive, Twitter, Youtube } from "lucide-react"

function ImportContent() {
  const { bumpListRevision } = useStore()
  const [urlInput, setUrlInput] = useState("")
  const [urlTags, setUrlTags] = useState("")
  const [urlLoading, setUrlLoading] = useState(false)
  const [urlResult, setUrlResult] = useState<{ ok: boolean; msg: string } | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const obsidianInputRef = useRef<HTMLInputElement>(null)
  const [fileLoading, setFileLoading] = useState(false)
  const [fileResult, setFileResult] = useState<{ ok: boolean; msg: string } | null>(null)

  const handleUrlImport = async () => {
    if (!urlInput.trim()) return
    setUrlLoading(true); setUrlResult(null)
    try {
      const tags = urlTags.split(",").map(t => t.trim()).filter(Boolean)
      const entry = await importApi.importUrl(urlInput.trim(), tags)
      setUrlResult({ ok: true, msg: `✓ 「${entry.title}」をインポートしました` })
      setUrlInput(""); setUrlTags("")
      bumpListRevision()
    } catch (e: unknown) {
      setUrlResult({ ok: false, msg: `エラー: ${e instanceof Error ? e.message : String(e)}` })
    }
    setUrlLoading(false)
  }

  const handleFileImport = async (file: File, type: "file" | "obsidian") => {
    setFileLoading(true); setFileResult(null)
    try {
      const res = type === "obsidian"
        ? await importApi.importObsidian(file)
        : await importApi.importFile(file)

      const msg = type === "obsidian"
        ? `✓ ${res.created}件のノートをインポートしました`
        : `✓ 「${res.title}」をインポートしました (${res.pages || "-"}ページ)`

      setFileResult({ ok: true, msg })
      bumpListRevision()
    } catch (e: unknown) {
      setFileResult({ ok: false, msg: `エラー: ${e instanceof Error ? e.message : String(e)}` })
    }
    setFileLoading(false)
  }

  const handleDrop = (e: React.DragEvent, type: "file" | "obsidian") => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) handleFileImport(file, type)
  }

  return (
    <div className="shell">
      <Topbar />
      <Sidebar />
      <main className="main-area" style={{ overflow: "auto" }}>
        <div className="import-panel">
          <h1 style={{ fontSize: 20, fontWeight: 900, letterSpacing: "-0.03em", color: "var(--text)" }}>
            インポート
          </h1>

          {/* URL Import */}
          <div className="import-section">
            <div className="import-section-title">
              <Globe size={14} /> URLスクレイプ
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <input
                type="url"
                value={urlInput}
                onChange={e => setUrlInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleUrlImport()}
                placeholder="https://..."
                className="form-input"
              />
              <input
                type="text"
                value={urlTags}
                onChange={e => setUrlTags(e.target.value)}
                placeholder="タグ (カンマ区切り・省略可)"
                className="form-input"
              />
              <button
                type="button"
                className="btn-primary"
                onClick={handleUrlImport}
                disabled={urlLoading || !urlInput.trim()}
              >
                {urlLoading ? "スクレイプ中…" : "インポート"}
              </button>
              {urlResult && (
                <p style={{ fontSize: 12, color: urlResult.ok ? "var(--green)" : "var(--red)" }}>
                  {urlResult.msg}
                </p>
              )}
            </div>
          </div>

          {/* File Import */}
          <div className="import-section">
            <div className="import-section-title">
              <FileText size={14} /> ファイル (PDF / DOCX / TXT)
            </div>
            <div
              className="dropzone"
              onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add("over") }}
              onDragLeave={e => e.currentTarget.classList.remove("over")}
              onDrop={e => { e.currentTarget.classList.remove("over"); handleDrop(e, "file") }}
              onClick={() => fileInputRef.current?.click()}
            >
              {fileLoading ? "処理中…" : "ファイルをドラッグ＆ドロップ、またはクリックして選択"}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              style={{ display: "none" }}
              onChange={e => { if (e.target.files?.[0]) handleFileImport(e.target.files[0], "file") }}
            />
            {fileResult && (
              <p style={{ fontSize: 12, marginTop: 8, color: fileResult.ok ? "var(--green)" : "var(--red)" }}>
                {fileResult.msg}
              </p>
            )}
          </div>

          {/* Obsidian Import */}
          <div className="import-section">
            <div className="import-section-title">
              <Archive size={14} /> Obsidian Vault (.zip)
            </div>
            <div
              className="dropzone"
              onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add("over") }}
              onDragLeave={e => e.currentTarget.classList.remove("over")}
              onDrop={e => { e.currentTarget.classList.remove("over"); handleDrop(e, "obsidian") }}
              onClick={() => obsidianInputRef.current?.click()}
            >
              Obsidian VaultのZIPをドロップ
            </div>
            <input
              ref={obsidianInputRef}
              type="file"
              accept=".zip"
              style={{ display: "none" }}
              onChange={e => { if (e.target.files?.[0]) handleFileImport(e.target.files[0], "obsidian") }}
            />
          </div>

          {/* Info cards */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {[
              { icon: <Twitter size={14} />, label: "X Archive", desc: "tweets.js / likes.js をAPI経由でインポート" },
              { icon: <Youtube size={14} />, label: "YouTube", desc: "高評価・プレイリストをYouTube API経由でインポート" },
            ].map(item => (
              <div key={item.label} style={{
                padding: "12px 14px",
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                opacity: 0.6,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 700, marginBottom: 4, color: "var(--text-muted)" }}>
                  {item.icon} {item.label}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-subtle)" }}>{item.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </main>
      <QuickAdd />
    </div>
  )
}

export default function ImportPage() {
  return (
    <SWRConfig value={{ revalidateOnFocus: false }}>
      <ImportContent />
    </SWRConfig>
  )
}
