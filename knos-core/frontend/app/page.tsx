// app/page.tsx
"use client"
import { useEffect } from "react"
import { Topbar } from "@/components/Topbar"
import { Sidebar } from "@/components/Sidebar"
import { EntryCard } from "@/components/EntryCard"
import { EntryDetail } from "@/components/EntryDetail"
import { QuickAdd } from "@/components/QuickAdd"
import { useEntries, useSearch } from "@/lib/hooks/useEntries"
import { useStore } from "@/lib/store"
import type { EntryType } from "@/lib/api"
import { SWRConfig } from "swr"

function HomeContent() {
  const {
    activeType, activeTag, searchQuery, searchMode,
    selectedEntry, setSelectedEntry, listRevision,
  } = useStore()

  const isSearching = searchQuery.trim().length > 0

  const { data: listData, isLoading: listLoading } = useEntries(
    isSearching ? undefined : {
      type: activeType as EntryType | undefined,
      tag: activeTag || undefined,
    }
  )

  const { data: searchData, isLoading: searchLoading } = useSearch(
    isSearching ? searchQuery : "",
    { type: activeType as EntryType | undefined, mode: searchMode }
  )

  const entries = isSearching
    ? (searchData?.results.map(r => r.entry) ?? [])
    : (listData?.items ?? [])

  const loading = isSearching ? searchLoading : listLoading

  // Clear selection when list changes
  useEffect(() => { setSelectedEntry(null) }, [activeType, activeTag, searchQuery, listRevision])

  return (
    <div className="shell">
      <Topbar />
      <Sidebar />

      <main className="main-area">
        <div className="split-layout">
          {/* Entry List */}
          <div style={{ overflow: "hidden", display: "flex", flexDirection: "column", borderRight: "1px solid var(--border)" }}>
            <div style={{
              padding: "10px 12px 8px",
              borderBottom: "1px solid var(--border)",
              fontSize: 11,
              color: "var(--text-subtle)",
              fontWeight: 700,
              letterSpacing: "0.05em",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}>
              {isSearching ? `「${searchQuery}」の検索結果` : (activeType || activeTag || "すべて")}
              {!loading && (
                <span style={{ fontWeight: 400, color: "var(--text-subtle)" }}>
                  {isSearching
                    ? `${searchData?.total ?? 0}件`
                    : `${listData?.total ?? 0}件`}
                </span>
              )}
              {isSearching && searchData && (
                <span style={{ marginLeft: "auto", color: "var(--text-subtle)", fontSize: 10 }}>
                  全文: {searchData.timing_ms.fulltext_ms ?? "-"}ms
                  {searchData.timing_ms.vector_ms && ` / vec: ${searchData.timing_ms.vector_ms}ms`}
                </span>
              )}
            </div>

            <div className="entry-list-panel">
              {loading && <div className="loading">読み込み中…</div>}
              {!loading && entries.length === 0 && (
                <div className="empty-state">
                  <div className="empty-icon">📭</div>
                  <p className="empty-text">エントリーが見つかりません</p>
                </div>
              )}
              {entries.map(e => <EntryCard key={e.id} entry={e} />)}
            </div>
          </div>

          {/* Detail Panel */}
          <div style={{ overflow: "hidden" }}>
            {selectedEntry ? (
              <EntryDetail entry={selectedEntry} />
            ) : (
              <div className="empty-state">
                <div className="empty-icon">⬡</div>
                <p className="empty-text">エントリーを選択してください</p>
              </div>
            )}
          </div>
        </div>
      </main>

      <QuickAdd />
    </div>
  )
}

export default function HomePage() {
  return (
    <SWRConfig value={{ revalidateOnFocus: false }}>
      <HomeContent />
    </SWRConfig>
  )
}
