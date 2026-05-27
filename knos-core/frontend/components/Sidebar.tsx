// components/Sidebar.tsx
"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Star, Trash2, Clock, Tag } from "lucide-react"
import { useStore } from "@/lib/store"
import { useTags } from "@/lib/hooks/useEntries"
import { cn, TYPE_META, ALL_TYPES } from "@/lib/utils"
import { useSrsStats } from "@/lib/hooks/useEntries"

export function Sidebar() {
  const { activeType, setActiveType, activeTag, setActiveTag } = useStore()
  const path = usePathname()
  const { data: tags } = useTags()
  const { data: srsStats } = useSrsStats()

  const isHome = path === "/"

  return (
    <nav className="sidebar">
      {/* Views */}
      <div className="sidebar-section">
        <div className="sidebar-section-label">ビュー</div>
        <Link
          href="/"
          className={cn("sidebar-item", isHome && !activeType && "active")}
          onClick={() => { setActiveType(""); setActiveTag("") }}
        >
          <span className="sidebar-item-icon">⬡</span>
          すべて
        </Link>
        <Link href="/" className={cn("sidebar-item", isHome && activeType === "" && activeTag === "" && false)}
          onClick={() => { setActiveType(""); setActiveTag(""); }}>
        </Link>
        <Link
          href="/?favorite=true"
          className={cn("sidebar-item", path.includes("favorite") && "active")}
        >
          <Star size={13} className="sidebar-item-icon" />
          スター付き
        </Link>
        <Link href="/srs" className={cn("sidebar-item", path === "/srs" && "active")}>
          <span className="sidebar-item-icon">🃏</span>
          SRS復習
          {srsStats && srsStats.due_today > 0 && (
            <span className="sidebar-item-count">{srsStats.due_today}</span>
          )}
        </Link>
        <Link href="/graph" className={cn("sidebar-item", path === "/graph" && "active")}>
          <span className="sidebar-item-icon">🕸</span>
          グラフ
        </Link>
        <Link href="/ai" className={cn("sidebar-item", path === "/ai" && "active")}>
          <span className="sidebar-item-icon">🤖</span>
          AI Ask
        </Link>
        <Link href="/import" className={cn("sidebar-item", path === "/import" && "active")}>
          <span className="sidebar-item-icon">📥</span>
          インポート
        </Link>
      </div>

      {/* Types */}
      <div className="sidebar-section">
        <div className="sidebar-section-label">タイプ</div>
        {ALL_TYPES.map(t => {
          const meta = TYPE_META[t]
          return (
            <button
              key={t}
              className={cn("sidebar-item", isHome && activeType === t && "active")}
              onClick={() => {
                setActiveType(activeType === t ? "" : t)
                setActiveTag("")
              }}
            >
              <span className="sidebar-item-icon">{meta.icon}</span>
              {meta.label}
            </button>
          )
        })}
      </div>

      {/* Tags */}
      {tags && tags.length > 0 && (
        <div className="sidebar-section">
          <div className="sidebar-section-label">タグ</div>
          {tags.slice(0, 20).map(tag => (
            <button
              key={tag.id}
              className={cn("sidebar-item", activeTag === tag.name && "active")}
              onClick={() => setActiveTag(activeTag === tag.name ? "" : tag.name)}
            >
              <Tag size={11} className="sidebar-item-icon" />
              {tag.name}
              <span className="sidebar-item-count">{tag.count}</span>
            </button>
          ))}
        </div>
      )}
    </nav>
  )
}
