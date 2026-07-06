import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import rehypeHighlight from 'rehype-highlight'
import { Copy, Check } from 'lucide-react'

/**
 * Fix malformed markdown: model sometimes puts bullet lists inside table
 * cells, leaking "| |" continuations onto bullet lines.
 */
export function sanitizeMarkdown(text) {
  if (!text) return text
  return text
    .split('\n')
    .map(line => {
      if (/^[-*] /.test(line) && line.includes(' | |')) return line.replace(/ \| \|.*$/, '')
      if (/^[-*] /.test(line) && / \|\s*$/.test(line)) return line.replace(/ \|\s*$/, '')
      return line
    })
    .join('\n')
}

function CodeBlock({ children }) {
  const [copied, setCopied] = useState(false)

  const copy = e => {
    const code = e.currentTarget.closest('.relative')?.querySelector('code')
    if (!code) return
    navigator.clipboard.writeText(code.innerText)
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  return (
    <div className="relative group/code">
      <button
        type="button"
        aria-label="Copy code"
        onClick={copy}
        className="absolute top-2.5 right-2.5 z-10 flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-medium opacity-0 group-hover/code:opacity-100 transition-all duration-200"
        style={{
          background: 'rgba(255,255,255,0.06)',
          border: '1px solid var(--border-med)',
          color: copied ? 'var(--success)' : 'var(--text-lo)',
        }}
      >
        {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
        {copied ? 'Copied' : 'Copy'}
      </button>
      <pre>{children}</pre>
    </div>
  )
}

const components = {
  pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
  table: ({ children }) => <div className="table-wrapper">{<table>{children}</table>}</div>,
}

/** Themed markdown renderer with math, GFM, syntax highlighting and copyable code. */
export function Markdown({ children }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex, rehypeHighlight]}
      components={components}
    >
      {sanitizeMarkdown(children)}
    </ReactMarkdown>
  )
}

export default Markdown
