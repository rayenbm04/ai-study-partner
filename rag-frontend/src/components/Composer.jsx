import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Paperclip, Link2, Send, Square, Zap, Cpu, Cloud, Loader2, X, ArrowRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { FileChip } from '@/components/FileCard'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

function ToolButton({ title, active, onClick, children }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <motion.button
          type="button"
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.92 }}
          aria-label={title}
          aria-pressed={active}
          onClick={onClick}
          className="h-8 w-8 rounded-sm flex items-center justify-center transition-colors duration-200"
          style={{
            color: active ? 'var(--accent-1)' : 'var(--text-lo)',
            background: active ? 'var(--accent-1-dim)' : 'transparent',
          }}
          onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
          onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
        >
          {children}
        </motion.button>
      </TooltipTrigger>
      <TooltipContent>{title}</TooltipContent>
    </Tooltip>
  )
}

/**
 * Floating glass composer: auto-growing textarea, attach / URL ingest,
 * provider + model selectors, streaming toggle and animated send button.
 */
export function Composer({
  value, onChange, onSubmit, onHistoryKey,
  isLoading, onCancel,
  streamMode, onToggleStream,
  onAttach,
  showUrl, onToggleUrl, urlValue, onUrlChange, onUrlSubmit, urlLoading,
  provider, onProviderChange, cloudModel, onCloudModelChange, cloudModels = [],
  files = [], onPreviewFile, onRemoveFile,
  footer,
  autoFocus,
}) {
  const taRef = useRef(null)

  // Auto-grow textarea
  useEffect(() => {
    const ta = taRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`
  }, [value])

  const handleKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!isLoading && value.trim()) onSubmit(e)
      return
    }
    if ((e.key === 'ArrowUp' || e.key === 'ArrowDown') && !value.includes('\n')) {
      onHistoryKey?.(e)
    }
  }

  return (
    <div className="w-full">
      {/* File chips */}
      <AnimatePresence>
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap gap-1.5 mb-2 overflow-hidden"
          >
            <AnimatePresence mode="popLayout">
              {files.map(file => (
                <FileChip key={file.name} file={file} onPreview={onPreviewFile} onRemove={onRemoveFile} />
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>

      {/* URL ingest row */}
      <AnimatePresence>
        {showUrl && (
          <motion.form
            initial={{ opacity: 0, y: 6, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, y: 6, height: 0 }}
            transition={{ type: 'spring', stiffness: 400, damping: 32 }}
            className="mb-2 overflow-hidden"
            onSubmit={onUrlSubmit}
          >
            <div className="glass flex items-center gap-1.5 rounded-md pl-3 pr-1.5 py-1.5">
              <Link2 className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--accent-2)' }} />
              <input
                autoFocus
                type="url"
                placeholder="Paste a URL to ingest…"
                aria-label="URL to ingest"
                value={urlValue}
                onChange={e => onUrlChange(e.target.value)}
                className="flex-1 bg-transparent text-xs outline-none placeholder:text-[var(--text-faint)]"
                style={{ color: 'var(--text-hi)' }}
              />
              <motion.button
                type="submit"
                whileHover={{ scale: 1.06 }}
                whileTap={{ scale: 0.94 }}
                disabled={urlLoading || !urlValue.trim()}
                aria-label="Ingest URL"
                className="h-7 w-7 rounded-sm flex items-center justify-center disabled:opacity-40 transition-opacity"
                style={{ background: 'var(--accent-1-dim)', color: 'var(--accent-1)' }}
              >
                {urlLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <ArrowRight className="w-3 h-3" />}
              </motion.button>
              <button
                type="button"
                aria-label="Close URL input"
                className="h-7 w-7 rounded-sm flex items-center justify-center hover:bg-white/5 transition-colors"
                style={{ color: 'var(--text-faint)' }}
                onClick={onToggleUrl}
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      {/* Composer shell */}
      <form onSubmit={onSubmit}>
        <div className="composer-shell glass-strong rounded-lg px-3 pt-3 pb-2">
          <textarea
            ref={taRef}
            rows={1}
            autoFocus={autoFocus}
            placeholder="Ask anything about your documents…"
            aria-label="Message"
            value={value}
            onChange={e => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            className="w-full resize-none bg-transparent text-sm outline-none leading-relaxed px-1 placeholder:text-[var(--text-faint)] disabled:opacity-60"
            style={{ color: 'var(--text-hi)', maxHeight: 200 }}
          />

          <div className="flex items-center gap-1 mt-1.5">
            <ToolButton title="Attach files" onClick={onAttach}>
              <Paperclip className="w-4 h-4" />
            </ToolButton>
            <ToolButton title="Ingest URL" active={showUrl} onClick={onToggleUrl}>
              <Link2 className="w-4 h-4" />
            </ToolButton>

            <div className="w-px h-4 mx-1" style={{ background: 'var(--border-med)' }} />

            {/* Provider selector */}
            <div
              className="flex items-center rounded-sm p-0.5 gap-0.5"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-soft)' }}
              role="radiogroup"
              aria-label="Model provider"
            >
              {[
                { key: 'local', label: 'Local', Icon: Cpu },
                { key: 'cloud', label: 'Groq', Icon: Cloud },
              ].map(({ key, label, Icon }) => {
                const active = provider === key
                return (
                  <button
                    key={key}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => onProviderChange(key)}
                    className="relative flex items-center gap-1 px-2 py-1 rounded-sm text-[10px] font-medium transition-colors duration-200"
                    style={{ color: active ? 'var(--text-hi)' : 'var(--text-faint)' }}
                  >
                    {active && (
                      <motion.span
                        layoutId="provider-pill"
                        className="absolute inset-0 rounded-sm"
                        style={{ background: 'var(--accent-1-dim)', border: '1px solid color-mix(in srgb, var(--primary) 30%, transparent)' }}
                        transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                      />
                    )}
                    <Icon className="w-2.5 h-2.5 relative z-10" style={active ? { color: 'var(--accent-1)' } : undefined} />
                    <span className="relative z-10">{label}</span>
                  </button>
                )
              })}
            </div>

            {/* Cloud model selector */}
            <AnimatePresence>
              {provider === 'cloud' && cloudModels.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 34 }}
                  className="overflow-hidden"
                >
                  <select
                    aria-label="Cloud model"
                    className="text-[10px] rounded-sm px-1.5 py-1.5 cursor-pointer outline-none max-w-[130px]"
                    style={{
                      background: 'rgba(255,255,255,0.04)',
                      border: '1px solid var(--border-soft)',
                      color: 'var(--text-lo)',
                    }}
                    value={cloudModel}
                    onChange={e => onCloudModelChange(e.target.value)}
                  >
                    {cloudModels.map(m => (
                      <option key={m.key} value={m.key}>{m.label}</option>
                    ))}
                  </select>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="flex-1" />

            <ToolButton
              title={streamMode ? 'Streaming on — click for instant' : 'Instant mode — click for streaming'}
              active={streamMode}
              onClick={onToggleStream}
            >
              <Zap className={cn('w-4 h-4', streamMode && 'fill-current')} />
            </ToolButton>

            {/* Send / stop */}
            {isLoading ? (
              <motion.button
                type="button"
                whileHover={{ scale: 1.06 }}
                whileTap={{ scale: 0.92 }}
                onClick={onCancel}
                aria-label="Stop generating"
                className="h-9 w-9 rounded-sm flex items-center justify-center flex-shrink-0"
                style={{
                  background: 'rgba(239,68,68,0.15)',
                  border: '1px solid rgba(239,68,68,0.35)',
                  color: 'var(--danger)',
                }}
              >
                <Square className="w-3.5 h-3.5 fill-current" />
              </motion.button>
            ) : (
              <motion.button
                type="submit"
                whileHover={value.trim() ? { scale: 1.06 } : undefined}
                whileTap={value.trim() ? { scale: 0.92 } : undefined}
                disabled={!value.trim()}
                aria-label="Send message"
                className="h-9 w-9 rounded-sm flex items-center justify-center flex-shrink-0 transition-all duration-300"
                style={
                  value.trim()
                    ? { background: 'var(--primary)', color: 'var(--primary-foreground)' }
                    : { background: 'rgba(255,255,255,0.05)', color: 'var(--text-faint)', cursor: 'not-allowed' }
                }
              >
                <Send className="w-4 h-4" />
              </motion.button>
            )}
          </div>
        </div>
      </form>

      {footer}
    </div>
  )
}

export default Composer
