// components/editor/Toolbar.tsx
'use client'

import type { Editor } from '@tiptap/react'
import {
  Bold, Italic, Underline, Strikethrough, Code, Link2, Link2Off,
  AlignLeft, AlignCenter, AlignRight,
  Heading1, Heading2, Heading3, Heading4,
  List, ListOrdered, CheckSquare,
  Quote, Minus, Table, Image,
  Video, Superscript, Subscript,
  Undo, Redo, RemoveFormatting,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { BlockTagPanel } from './BlockTagPanel'

const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899', '#000000']
const HIGHLIGHTS = ['#fef08a', '#bbf7d0', '#bfdbfe', '#f5d0fe', '#fed7aa', 'transparent']

interface ToolbarProps {
  editor: Editor
}

function ToolBtn({
  onClick, active, disabled, title, children, className
}: {
  onClick: () => void
  active?: boolean
  disabled?: boolean
  title?: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn('toolbar-btn', active && 'toolbar-btn-active', className)}
    >
      {children}
    </button>
  )
}

function Divider() {
  return <div className="toolbar-divider" />
}

export function Toolbar({ editor }: ToolbarProps) {
  const setLink = () => {
    const prev = editor.getAttributes('link').href
    const url = prompt('URLを入力:', prev || 'https://')
    if (url === null) return
    if (url === '') {
      editor.chain().focus().unsetLink().run()
      return
    }
    editor.chain().focus().setLink({ href: url }).run()
  }

  const insertMath = () => {
    const latex = prompt('LaTeX数式を入力:')
    if (latex != null) {
      ;(editor.chain().focus() as unknown as { insertMathBlock: (s: string) => { run: () => void } })
        .insertMathBlock(latex).run()
    }
  }

  const insertVideo = () => {
    const url = prompt('YouTube/Vimeo URLを入力:')
    if (url)
      (editor.chain().focus() as unknown as { insertVideo: (u: string) => { run: () => void } })
        .insertVideo(url).run()
  }

  const insertImage = () => {
    const url = prompt('画像URLを入力:')
    if (url) editor.chain().focus().setImage({ src: url }).run()
  }

  return (
    <div className="toolbar" role="toolbar" aria-label="エディターツールバー">
      {/* 元に戻す / やり直し */}
      <ToolBtn onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} title="元に戻す">
        <Undo size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} title="やり直し">
        <Redo size={14} />
      </ToolBtn>
      <Divider />

      {/* 見出し */}
      <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} active={editor.isActive('heading', { level: 1 })} title="見出し1">
        <Heading1 size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} active={editor.isActive('heading', { level: 2 })} title="見出し2">
        <Heading2 size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} active={editor.isActive('heading', { level: 3 })} title="見出し3">
        <Heading3 size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleHeading({ level: 4 }).run()} active={editor.isActive('heading', { level: 4 })} title="見出し4">
        <Heading4 size={14} />
      </ToolBtn>
      <Divider />

      {/* テキスト装飾 */}
      <ToolBtn onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="太字 (⌘B)">
        <Bold size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="斜体 (⌘I)">
        <Italic size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleUnderline().run()} active={editor.isActive('underline')} title="下線 (⌘U)">
        <Underline size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleStrike().run()} active={editor.isActive('strike')} title="取り消し線">
        <Strikethrough size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleCode().run()} active={editor.isActive('code')} title="インラインコード">
        <Code size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleSuperscript().run()} active={editor.isActive('superscript')} title="上付き文字">
        <Superscript size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleSubscript().run()} active={editor.isActive('subscript')} title="下付き文字">
        <Subscript size={14} />
      </ToolBtn>
      <Divider />

      {/* 文字色 */}
      <div className="toolbar-color-group" title="文字色">
        {COLORS.map((color) => (
          <button
            key={color}
            type="button"
            className="color-dot"
            style={{ background: color, border: color === '#000000' ? '1px solid #e5e7eb' : 'none' }}
            onClick={() => editor.chain().focus().setColor(color).run()}
            title={color}
          />
        ))}
        <button
          type="button"
          className="color-dot color-dot-clear"
          onClick={() => editor.chain().focus().unsetColor().run()}
          title="色をリセット"
        >
          ✕
        </button>
      </div>

      {/* ハイライト */}
      <div className="toolbar-color-group" title="ハイライト">
        {HIGHLIGHTS.map((color) => (
          <button
            key={color}
            type="button"
            className="color-dot"
            style={{
              background: color === 'transparent' ? 'white' : color,
              border: '1px solid #e5e7eb',
            }}
            onClick={() =>
              color === 'transparent'
                ? editor.chain().focus().unsetHighlight().run()
                : editor.chain().focus().setHighlight({ color }).run()
            }
            title={color === 'transparent' ? 'ハイライトを解除' : color}
          />
        ))}
      </div>
      <Divider />

      {/* テキスト配置 */}
      <ToolBtn onClick={() => editor.chain().focus().setTextAlign('left').run()} active={editor.isActive({ textAlign: 'left' })} title="左揃え">
        <AlignLeft size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().setTextAlign('center').run()} active={editor.isActive({ textAlign: 'center' })} title="中央揃え">
        <AlignCenter size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().setTextAlign('right').run()} active={editor.isActive({ textAlign: 'right' })} title="右揃え">
        <AlignRight size={14} />
      </ToolBtn>
      <Divider />

      {/* リスト */}
      <ToolBtn onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="箇条書き">
        <List size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="番号リスト">
        <ListOrdered size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleTaskList().run()} active={editor.isActive('taskList')} title="チェックリスト">
        <CheckSquare size={14} />
      </ToolBtn>
      <Divider />

      {/* ブロック */}
      <ToolBtn onClick={() => editor.chain().focus().toggleBlockquote().run()} active={editor.isActive('blockquote')} title="引用">
        <Quote size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().toggleCodeBlock().run()} active={editor.isActive('codeBlock')} title="コードブロック">
        <Code size={14} />
      </ToolBtn>
      <ToolBtn onClick={() => editor.chain().focus().setHorizontalRule().run()} title="区切り線">
        <Minus size={14} />
      </ToolBtn>
      <ToolBtn
        onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}
        title="テーブル"
      >
        <Table size={14} />
      </ToolBtn>
      <Divider />

      {/* リンク / 画像 / 動画 / 数式 */}
      <ToolBtn onClick={setLink} active={editor.isActive('link')} title="リンク (⌘K)">
        <Link2 size={14} />
      </ToolBtn>
      {editor.isActive('link') && (
        <ToolBtn onClick={() => editor.chain().focus().unsetLink().run()} title="リンクを削除">
          <Link2Off size={14} />
        </ToolBtn>
      )}
      <ToolBtn onClick={insertImage} title="画像を挿入">
        <Image size={14} />
      </ToolBtn>
      <ToolBtn onClick={insertVideo} title="動画を埋め込み">
        <Video size={14} />
      </ToolBtn>
      <ToolBtn onClick={insertMath} title="数式ブロック (⌘⇧M)">
        <span className="text-sm font-serif">∑</span>
      </ToolBtn>
      <Divider />

      {/* ブロックタグ */}
      <BlockTagPanel editor={editor} />
      <Divider />

      {/* 書式をクリア */}
      <ToolBtn onClick={() => editor.chain().focus().clearNodes().unsetAllMarks().run()} title="書式をクリア">
        <RemoveFormatting size={14} />
      </ToolBtn>
    </div>
  )
}
