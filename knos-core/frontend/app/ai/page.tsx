// app/ai/page.tsx
"use client"
import { useState, useRef, useEffect } from "react"
import { SWRConfig } from "swr"
import { Topbar } from "@/components/Topbar"
import { Sidebar } from "@/components/Sidebar"
import { QuickAdd } from "@/components/QuickAdd"
import { aiApi } from "@/lib/api"
import { Send } from "lucide-react"

interface Message {
  role: "user" | "assistant"
  content: string
  sources?: string[]
}

const SUGGESTIONS = [
  "先週読んだ記事で、AIに関するものを教えて",
  "定義タイプのエントリーを一覧で説明して",
  "最近追加したリンクの共通テーマは？",
  "未読のウェブページで重要そうなものは？",
]

function AiContent() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const send = async (text?: string) => {
    const q = (text || input).trim()
    if (!q || loading) return

    setInput("")
    setMessages(prev => [...prev, { role: "user", content: q }])
    setLoading(true)

    try {
      const res = await aiApi.ask(q, true)
      setMessages(prev => [...prev, {
        role: "assistant",
        content: res.answer,
        sources: res.sources,
      }])
    } catch (e: unknown) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `エラー: ${e instanceof Error ? e.message : String(e)}`,
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="shell">
      <Topbar />
      <Sidebar />
      <main className="main-area">
        <div className="ai-panel">
          <div className="ai-messages">
            {messages.length === 0 && (
              <div style={{ padding: "20px 0" }}>
                <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16 }}>
                  KnOS内のエントリーをコンテキストに、Geminiに質問できます。
                </p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {SUGGESTIONS.map(s => (
                    <button
                      key={s}
                      type="button"
                      className="action-btn"
                      style={{ fontSize: 12 }}
                      onClick={() => send(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className="ai-msg">
                <div className={`ai-msg-role ${msg.role}`}>
                  {msg.role === "user" ? "あなた" : "KnOS AI"}
                </div>
                <div className="ai-msg-body">{msg.content}</div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="ai-sources">
                    <span style={{ fontSize: 10, color: "var(--text-subtle)" }}>参照:</span>
                    {msg.sources.map((s, j) => (
                      <span key={j} className="ai-source-chip">{s.slice(0, 30)}{s.length > 30 ? "…" : ""}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="ai-msg">
                <div className="ai-msg-role assistant">KnOS AI</div>
                <div className="ai-msg-body" style={{ color: "var(--text-muted)" }}>
                  考え中
                  <span style={{ display: "inline-block", animation: "pulse 1s infinite" }}>…</span>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          <div className="ai-input-row">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="質問を入力… (Enter で送信、Shift+Enter で改行)"
              className="ai-input"
              rows={2}
              disabled={loading}
            />
            <button
              type="button"
              className="ai-send-btn"
              onClick={() => send()}
              disabled={loading || !input.trim()}
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      </main>
      <QuickAdd />
    </div>
  )
}

export default function AiPage() {
  return (
    <SWRConfig value={{ revalidateOnFocus: false }}>
      <AiContent />
    </SWRConfig>
  )
}
