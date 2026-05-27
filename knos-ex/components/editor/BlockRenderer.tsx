// components/editor/BlockRenderer.tsx
'use client'

import { useEffect, useRef } from 'react'
import { generateHTML } from '@tiptap/html'
import type { JSONContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import TextStyle from '@tiptap/extension-text-style'
import { Color } from '@tiptap/extension-color'
import Highlight from '@tiptap/extension-highlight'
import Underline from '@tiptap/extension-underline'
import Superscript from '@tiptap/extension-superscript'
import Subscript from '@tiptap/extension-subscript'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import Image from '@tiptap/extension-image'
import Link from '@tiptap/extension-link'
import TextAlign from '@tiptap/extension-text-align'
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import { createLowlight } from 'lowlight'
import { BlockId, MathInline, MathBlock, Callout, Video, Details } from '@/lib/editor/extensions'
import { cn } from '@/lib/utils'

const lowlight = createLowlight()

const extensions = [
  StarterKit.configure({ codeBlock: false }),
  TextStyle,
  Color,
  Highlight.configure({ multicolor: true }),
  Underline,
  Superscript,
  Subscript,
  TaskList,
  TaskItem.configure({ nested: true }),
  Table.configure({ resizable: false }),
  TableRow,
  TableCell,
  TableHeader,
  Image.configure({ inline: false }),
  Link.configure({ openOnClick: true }),
  TextAlign.configure({ types: ['heading', 'paragraph'] }),
  CodeBlockLowlight.configure({ lowlight }),
  BlockId,
  MathInline,
  MathBlock,
  Callout,
  Video,
  Details,
]

interface BlockRendererProps {
  blocks: JSONContent
  className?: string
}

export function BlockRenderer({ blocks, className }: BlockRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  let html = ''
  try {
    html = generateHTML(blocks, extensions)
  } catch {
    html = '<p>コンテンツの表示に失敗しました。</p>'
  }

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // KaTeX レンダリング
    const renderKatex = async () => {
      const katex = await import('katex')

      // インライン数式
      container.querySelectorAll('[data-math-inline]').forEach((el) => {
        const latex = el.getAttribute('data-latex') || el.textContent || ''
        try {
          el.innerHTML = katex.default.renderToString(latex, {
            throwOnError: false,
            displayMode: false,
          })
        } catch {
          // keep original
        }
      })

      // ブロック数式
      container.querySelectorAll('[data-math-block]').forEach((el) => {
        const latex = el.getAttribute('data-latex') || el.textContent || ''
        try {
          el.innerHTML = katex.default.renderToString(latex, {
            throwOnError: false,
            displayMode: true,
          })
        } catch {
          // keep original
        }
      })
    }

    renderKatex()

    // コードブロックにコピーボタンを追加
    container.querySelectorAll('pre').forEach((pre) => {
      if (pre.querySelector('.copy-btn')) return

      const btn = document.createElement('button')
      btn.className = 'copy-btn'
      btn.textContent = 'copy'
      btn.onclick = async () => {
        const code = pre.querySelector('code')?.textContent || ''
        await navigator.clipboard.writeText(code)
        btn.textContent = 'copied!'
        btn.classList.add('copied')
        setTimeout(() => {
          btn.textContent = 'copy'
          btn.classList.remove('copied')
        }, 2000)
      }
      pre.style.position = 'relative'
      pre.appendChild(btn)
    })

    // 動画 iframeレンダリング
    container.querySelectorAll('[data-video]').forEach((el) => {
      const src = el.getAttribute('data-src') || ''
      if (!src || el.querySelector('iframe')) return

      let embedUrl = ''
      const ytMatch = src.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/)
      if (ytMatch) embedUrl = `https://www.youtube.com/embed/${ytMatch[1]}`
      const vimeoMatch = src.match(/vimeo\.com\/(\d+)/)
      if (vimeoMatch) embedUrl = `https://player.vimeo.com/video/${vimeoMatch[1]}`

      if (embedUrl) {
        const iframe = document.createElement('iframe')
        iframe.src = embedUrl
        iframe.allowFullscreen = true
        iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture'
        iframe.style.cssText = 'width:100%;aspect-ratio:16/9;border:none;'
        el.innerHTML = ''
        el.appendChild(iframe)
      }
    })
  }, [html])

  return (
    <div
      ref={containerRef}
      className={cn('block-renderer prose prose-slate dark:prose-invert max-w-none', className)}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
