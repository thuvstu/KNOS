// components/editor/BlockTagPanel.tsx
'use client'

import { useState, KeyboardEvent } from 'react'
import type { Editor } from '@tiptap/react'
import { Tag, X, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface BlockTagPanelProps {
  editor: Editor
  className?: string
}

export function BlockTagPanel({ editor, className }: BlockTagPanelProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [input, setInput] = useState('')

  // 現在選択されているブロックのタグを取得
  const { selection } = editor.state
  const node = editor.state.doc.nodeAt(selection.from)
  const parentPos = editor.state.selection.$from.start(1) - 1
  const parentNode = parentPos >= 0 ? editor.state.doc.nodeAt(parentPos) : null
  const targetNode = parentNode || node
  const currentTagsRaw = (targetNode?.attrs?.['data-block-tags'] as string) || ''
  const currentTags = currentTagsRaw.split(',').map((t) => t.trim()).filter(Boolean)

  const updateTags = (tags: string[]) => {
    const { selection } = editor.state
    const pos = editor.state.selection.$from.start(1) - 1
    if (pos >= 0) {
      const n = editor.state.doc.nodeAt(pos)
      if (n) {
        editor.chain().command(({ tr }) => {
          tr.setNodeMarkup(pos, undefined, {
            ...n.attrs,
            'data-block-tags': tags.join(','),
          })
          return true
        }).run()
      }
    }
  }

  const addTag = () => {
    const tag = input.trim()
    if (!tag || currentTags.includes(tag)) {
      setInput('')
      return
    }
    updateTags([...currentTags, tag])
    setInput('')
  }

  const removeTag = (tag: string) => {
    updateTags(currentTags.filter((t) => t !== tag))
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addTag()
    }
    if (e.key === 'Escape') setIsOpen(false)
  }

  return (
    <div className={cn('relative', className)}>
      <button
        type="button"
        title="ブロックタグを追加"
        onClick={() => setIsOpen((v) => !v)}
        className={cn(
          'toolbar-btn',
          isOpen && 'toolbar-btn-active',
          currentTags.length > 0 && 'text-amber-500'
        )}
      >
        <Tag size={14} />
        {currentTags.length > 0 && (
          <span className="ml-0.5 text-xs font-bold">{currentTags.length}</span>
        )}
      </button>

      {isOpen && (
        <div className="block-tag-panel">
          <div className="block-tag-panel-header">
            <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">
              ブロックタグ
            </span>
          </div>

          <div className="block-tag-list">
            {currentTags.map((tag) => (
              <span key={tag} className="block-tag-chip">
                #{tag}
                <button
                  type="button"
                  onClick={() => removeTag(tag)}
                  className="block-tag-chip-remove"
                >
                  <X size={10} />
                </button>
              </span>
            ))}
            {currentTags.length === 0 && (
              <span className="text-xs text-gray-400">タグなし</span>
            )}
          </div>

          <div className="block-tag-input-row">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="タグを入力..."
              className="block-tag-input"
              autoFocus
            />
            <button type="button" onClick={addTag} className="block-tag-add-btn">
              <Plus size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
