// app/entries/[id]/page.tsx
"use client"
import { use } from "react"
import { SWRConfig } from "swr"
import { Topbar } from "@/components/Topbar"
import { Sidebar } from "@/components/Sidebar"
import { EntryDetail } from "@/components/EntryDetail"
import { QuickAdd } from "@/components/QuickAdd"
import { useEntry } from "@/lib/hooks/useEntries"

function EntryPageContent({ id }: { id: string }) {
  const { data: entry, isLoading } = useEntry(id)

  if (isLoading) return (
    <div className="shell">
      <Topbar />
      <Sidebar />
      <main className="main-area">
        <div className="loading">読み込み中…</div>
      </main>
    </div>
  )

  if (!entry) return (
    <div className="shell">
      <Topbar />
      <Sidebar />
      <main className="main-area">
        <div className="empty-state">
          <div className="empty-icon">❓</div>
          <p className="empty-text">エントリーが見つかりません</p>
        </div>
      </main>
    </div>
  )

  return (
    <div className="shell">
      <Topbar />
      <Sidebar />
      <main className="main-area" style={{ overflow: "auto" }}>
        <EntryDetail entry={entry} />
      </main>
      <QuickAdd />
    </div>
  )
}

export default function EntryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return (
    <SWRConfig value={{ revalidateOnFocus: false }}>
      <EntryPageContent id={id} />
    </SWRConfig>
  )
}
