// app/srs/page.tsx
"use client"
import { useState } from "react"
import { SWRConfig, mutate } from "swr"
import { Topbar } from "@/components/Topbar"
import { Sidebar } from "@/components/Sidebar"
import { QuickAdd } from "@/components/QuickAdd"
import { useSrsQueue, useSrsStats } from "@/lib/hooks/useEntries"
import { srsApi } from "@/lib/api"
import type { SrsQueueItem } from "@/lib/api"

const GRADES: Array<{ grade: number; label: string; desc: string }> = [
  { grade: 0, label: "完全に忘れた",    desc: "明日また" },
  { grade: 1, label: "難しかった",       desc: "1日後" },
  { grade: 2, label: "かろうじて",       desc: "2日後" },
  { grade: 3, label: "まあまあ",         desc: "数日後" },
  { grade: 4, label: "簡単だった",       desc: "数週間後" },
  { grade: 5, label: "完璧",             desc: "数ヶ月後" },
]

function SrsContent() {
  const { data, isLoading, mutate: mutateQueue } = useSrsQueue(20)
  const { data: stats, mutate: mutateStats } = useSrsStats()
  const [idx, setIdx] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [reviewing, setReviewing] = useState(false)
  const [done, setDone] = useState(false)

  const queue: SrsQueueItem[] = data?.queue ?? []
  const current = queue[idx]

  const handleGrade = async (grade: number) => {
    if (!current || reviewing) return
    setReviewing(true)
    await srsApi.record(current.entry_id, grade).catch(() => null)
    setReviewing(false)

    if (idx + 1 >= queue.length) {
      setDone(true)
    } else {
      setIdx(i => i + 1)
      setRevealed(false)
    }
    mutateStats()
  }

  if (isLoading) return <div className="loading">読み込み中…</div>

  return (
    <div className="shell">
      <Topbar />
      <Sidebar />
      <main className="main-area" style={{ overflow: "auto" }}>
        <div style={{ maxWidth: 600, margin: "0 auto", padding: "24px 16px" }}>

          {/* Stats bar */}
          {stats && (
            <div style={{
              display: "flex",
              gap: 20,
              marginBottom: 24,
              padding: "12px 16px",
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-lg)",
            }}>
              <div>
                <div style={{ fontSize: 20, fontWeight: 900, color: "var(--accent)" }}>{stats.due_today}</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>今日の復習</div>
              </div>
              <div>
                <div style={{ fontSize: 20, fontWeight: 900, color: "var(--text)" }}>{stats.total_enrolled}</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>登録済み</div>
              </div>
              <div style={{ marginLeft: "auto", display: "flex", alignItems: "center" }}>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                  {idx}/{queue.length} 完了
                </div>
              </div>
            </div>
          )}

          {/* Progress */}
          {queue.length > 0 && !done && (
            <div style={{
              height: 3,
              background: "var(--border)",
              borderRadius: 99,
              marginBottom: 20,
              overflow: "hidden",
            }}>
              <div style={{
                height: "100%",
                width: `${(idx / queue.length) * 100}%`,
                background: "var(--accent)",
                borderRadius: 99,
                transition: "width 0.3s",
              }} />
            </div>
          )}

          {done || queue.length === 0 ? (
            <div className="empty-state" style={{ minHeight: 300 }}>
              <div className="empty-icon">🎉</div>
              <p className="empty-text">今日の復習は完了です！</p>
              <button
                type="button"
                className="action-btn"
                style={{ marginTop: 12 }}
                onClick={() => { setIdx(0); setDone(false); setRevealed(false); mutateQueue() }}
              >
                もう一度
              </button>
            </div>
          ) : (
            <div className="srs-card">
              {/* Header */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                <span style={{ fontSize: 11, color: "var(--text-subtle)", fontWeight: 700 }}>
                  {idx + 1} / {queue.length}
                </span>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  次回: {current.next_review} · 間隔: {current.interval}日
                </span>
              </div>

              {/* Term */}
              <div className="srs-term">{current.title}</div>

              {/* Reveal */}
              {!revealed ? (
                <button
                  type="button"
                  className="srs-reveal-btn"
                  onClick={() => setRevealed(true)}
                >
                  答えを見る (Space)
                </button>
              ) : (
                <>
                  {/* Answer */}
                  {current.content && (
                    <div style={{
                      padding: "14px 16px",
                      background: "var(--bg-hover)",
                      border: "1px solid var(--border-mid)",
                      borderRadius: "var(--radius)",
                      fontSize: 14,
                      lineHeight: 1.65,
                      color: "var(--text)",
                      whiteSpace: "pre-wrap",
                      marginBottom: 20,
                    }}>
                      {current.content.slice(0, 800)}
                    </div>
                  )}

                  {/* Grade buttons */}
                  <div className="srs-grade-row">
                    {GRADES.map(({ grade, label, desc }) => (
                      <button
                        key={grade}
                        type="button"
                        className={`srs-grade-btn srs-grade-${grade}`}
                        onClick={() => handleGrade(grade)}
                        disabled={reviewing}
                      >
                        <div>{label}</div>
                        <div style={{ fontSize: 10, opacity: 0.7, marginTop: 2 }}>{desc}</div>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </main>
      <QuickAdd />
    </div>
  )
}

export default function SrsPage() {
  return (
    <SWRConfig value={{ revalidateOnFocus: false }}>
      <SrsContent />
    </SWRConfig>
  )
}
