// components/Topbar.tsx
"use client"
import { useRef } from "react"
import Link from "next/link"
import { Search, Plus, Network, BookOpen, Brain, Download, Settings } from "lucide-react"
import { useStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import { usePathname } from "next/navigation"

export function Topbar() {
  const { searchQuery, setSearchQuery, searchMode, setSearchMode, setQuickAddOpen } = useStore()
  const inputRef = useRef<HTMLInputElement>(null)
  const path = usePathname()

  const modes: Array<{ v: "hybrid" | "fulltext" | "semantic"; label: string }> = [
    { v: "hybrid",    label: "H" },
    { v: "fulltext",  label: "FT" },
    { v: "semantic",  label: "AI" },
  ]

  return (
    <header className="topbar">
      <Link href="/" className="topbar-logo">
        <span className="topbar-logo-icon">⬡</span>
        KnOS
      </Link>

      <div className="topbar-search-wrapper">
        <Search size={14} className="topbar-search-icon" />
        <input
          ref={inputRef}
          type="text"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          onKeyDown={e => e.key === "Escape" && setSearchQuery("")}
          placeholder="検索… (⌘K)"
          className="topbar-search"
        />
        <div className="topbar-search-mode">
          {modes.map(m => (
            <button
              key={m.v}
              type="button"
              className={cn("mode-chip", searchMode === m.v && "active")}
              onClick={() => setSearchMode(m.v)}
              title={m.v}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div className="topbar-right">
        <Link href="/graph" className={cn("topbar-icon-btn", path === "/graph" && "active")} title="グラフ">
          <Network size={16} />
        </Link>
        <Link href="/srs" className={cn("topbar-icon-btn", path === "/srs" && "active")} title="SRS復習">
          <BookOpen size={16} />
        </Link>
        <Link href="/ai" className={cn("topbar-icon-btn", path === "/ai" && "active")} title="AI">
          <Brain size={16} />
        </Link>
        <Link href="/import" className={cn("topbar-icon-btn", path === "/import" && "active")} title="インポート">
          <Download size={16} />
        </Link>
        <button
          type="button"
          className="topbar-icon-btn active"
          style={{ background: "var(--accent)", color: "#fff", borderColor: "var(--accent)" }}
          onClick={() => setQuickAddOpen(true)}
          title="新規エントリー (⌘N)"
        >
          <Plus size={16} />
        </button>
      </div>
    </header>
  )
}
