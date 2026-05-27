// app/graph/page.tsx
"use client"
import { useState, useCallback, useEffect } from "react"
import { SWRConfig } from "swr"
import { Topbar } from "@/components/Topbar"
import { Sidebar } from "@/components/Sidebar"
import { ForceGraph } from "@/components/ForceGraph"
import { QuickAdd } from "@/components/QuickAdd"
import { useGraph, useCandidates } from "@/lib/hooks/useEntries"
import { useStore } from "@/lib/store"
import { graphApi, entriesApi } from "@/lib/api"
import { mutate } from "swr"
import { ZoomIn, ZoomOut, RefreshCw, GitMerge } from "lucide-react"

function GraphContent() {
  const { graphDepth, setGraphDepth } = useStore()
  const [focusId, setFocusId] = useState<string | null>(null)
  const [showCandidates, setShowCandidates] = useState(false)
  const [containerSize, setContainerSize] = useState({ w: 800, h: 600 })
  const [entryTitle, setEntryTitle] = useState<string>("")

  const { data: graphData, isLoading } = useGraph(focusId, graphDepth)
  const { data: candidates } = useCandidates()

  const containerRef = useCallback((node: HTMLDivElement | null) => {
    if (!node) return
    const ro = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect
      setContainerSize({ w: width, h: height })
    })
    ro.observe(node)
    return () => ro.disconnect()
  }, [])

  const handleNodeClick = async (nodeId: string) => {
    setFocusId(nodeId)
    const entry = await entriesApi.get(nodeId).catch(() => null)
    if (entry) setEntryTitle(entry.title)
  }

  const handleCandidateAction = async (id: string, action: "approve" | "reject") => {
    await graphApi.actOnCandidate(id, action)
    mutate("candidates")
  }

  return (
    <div className="shell">
      <Topbar />
      <Sidebar />

      <main className="main-area" style={{ flexDirection: "column", overflow: "hidden" }}>
        {/* Toolbar */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "8px 14px",
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-panel)",
          flexShrink: 0,
        }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
            {focusId ? `📍 ${entryTitle || focusId.slice(0, 8)}` : "エントリーをクリックしてフォーカス"}
          </span>
          <span style={{ fontSize: 11, color: "var(--text-subtle)" }}>深度:</span>
          {[1, 2, 3, 4].map(d => (
            <button
              key={d}
              type="button"
              className={`mode-chip ${graphDepth === d ? "active" : ""}`}
              onClick={() => setGraphDepth(d)}
            >
              {d}
            </button>
          ))}
          {focusId && (
            <button type="button" className="action-btn" onClick={() => setFocusId(null)}>
              <RefreshCw size={12} /> リセット
            </button>
          )}
          {candidates && candidates.length > 0 && (
            <button
              type="button"
              className={`action-btn ${showCandidates ? "active" : ""}`}
              onClick={() => setShowCandidates(v => !v)}
              style={{ marginLeft: "auto" }}
            >
              <GitMerge size={12} />
              接続候補 {candidates.length}件
            </button>
          )}
        </div>

        <div style={{ flex: 1, overflow: "hidden", display: "flex" }}>
          {/* Graph */}
          <div ref={containerRef} className="graph-container" style={{ flex: 1 }}>
            {isLoading && (
              <div className="loading">グラフ生成中…</div>
            )}
            {!isLoading && graphData && graphData.nodes.length > 0 ? (
              <ForceGraph
                data={graphData}
                onNodeClick={handleNodeClick}
                width={containerSize.w}
                height={containerSize.h}
              />
            ) : !isLoading && (
              <div className="empty-state">
                <div className="empty-icon">🕸</div>
                <p className="empty-text">
                  {focusId ? "接続がありません" : "エントリーをクリックしてグラフを表示"}
                </p>
              </div>
            )}
          </div>

          {/* Candidates Panel */}
          {showCandidates && candidates && (
            <div style={{
              width: 320,
              borderLeft: "1px solid var(--border)",
              overflow: "auto",
              padding: 12,
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)", marginBottom: 4 }}>
                接続候補 (類似度順)
              </div>
              {candidates.map(c => (
                <div key={c.id} className="candidate-card">
                  <div className="candidate-score">
                    {(c.score * 100).toFixed(0)}%
                  </div>
                  <div className="candidate-names">
                    <h4>{c.entry_a.slice(0, 8)}…</h4>
                    <span>↔ {c.entry_b.slice(0, 8)}…</span>
                  </div>
                  <div className="candidate-actions">
                    <button
                      type="button"
                      className="action-btn"
                      style={{ padding: "4px 10px", fontSize: 11 }}
                      onClick={() => handleCandidateAction(c.id, "approve")}
                    >
                      ✓
                    </button>
                    <button
                      type="button"
                      className="action-btn danger"
                      style={{ padding: "4px 10px", fontSize: 11 }}
                      onClick={() => handleCandidateAction(c.id, "reject")}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      <QuickAdd />
    </div>
  )
}

export default function GraphPage() {
  return (
    <SWRConfig value={{ revalidateOnFocus: false }}>
      <GraphContent />
    </SWRConfig>
  )
}
