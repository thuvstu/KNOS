// components/editor/RichEditor.tsx
'use client'

import { EditorContent } from '@tiptap/react'
import type { JSONContent } from '@tiptap/react'
import { useEditorConfig } from '@/lib/editor/useEditorConfig'
import { Toolbar } from './Toolbar'
import { cn } from '@/lib/utils'

interface RichEditorProps {
  content?: JSONContent | string
  onChange?: (doc: JSONContent) => void
  placeholder?: string
  className?: string
  minHeight?: string
}

export function RichEditor({
  content,
  onChange,
  placeholder,
  className,
  minHeight = '300px',
}: RichEditorProps) {
  const editor = useEditorConfig({
    content,
    placeholder,
    onUpdate: onChange,
  })

  if (!editor) return null

  return (
    <div className={cn('rich-editor-wrapper', className)}>
      <Toolbar editor={editor} />
      <EditorContent
        editor={editor}
        className="rich-editor-content"
        style={{ minHeight }}
      />
    </div>
  )
}
