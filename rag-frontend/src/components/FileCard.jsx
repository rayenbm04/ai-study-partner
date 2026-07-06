import { motion } from 'framer-motion'
import {
  FileText, FileSpreadsheet, FileImage, Presentation, Globe, FileCode,
  Loader2, RotateCcw, X, Eye,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const EXT_META = {
  pdf:  { Icon: FileText,        color: '#F87171' },
  docx: { Icon: FileText,        color: '#60A5FA' },
  doc:  { Icon: FileText,        color: '#60A5FA' },
  pptx: { Icon: Presentation,    color: '#FB923C' },
  xlsx: { Icon: FileSpreadsheet, color: '#34D399' },
  xls:  { Icon: FileSpreadsheet, color: '#34D399' },
  csv:  { Icon: FileSpreadsheet, color: '#34D399' },
  png:  { Icon: FileImage,       color: '#4CC9F0' },
  jpg:  { Icon: FileImage,       color: '#4CC9F0' },
  jpeg: { Icon: FileImage,       color: '#4CC9F0' },
  gif:  { Icon: FileImage,       color: '#4CC9F0' },
  webp: { Icon: FileImage,       color: '#4CC9F0' },
  bmp:  { Icon: FileImage,       color: '#4CC9F0' },
  md:   { Icon: FileCode,        color: '#A78BFA' },
  txt:  { Icon: FileText,        color: '#A1A1AA' },
  puml: { Icon: FileCode,        color: '#A78BFA' },
  html: { Icon: Globe,           color: '#4CC9F0' },
}

export function fileMeta(name) {
  const ext = (name || '').split('.').pop().toLowerCase()
  return EXT_META[ext] || { Icon: FileText, color: '#A1A1AA' }
}

export function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const STATUS = {
  uploading: { label: 'Uploading', color: 'var(--text-lo)',  bg: 'rgba(255,255,255,0.06)' },
  indexing:  { label: 'Indexing',  color: 'var(--warning)',  bg: 'rgba(245,158,11,0.12)' },
  ready:     { label: 'Ready',     color: 'var(--success)',  bg: 'rgba(34,197,94,0.12)' },
  error:     { label: 'Error',     color: 'var(--danger)',   bg: 'rgba(239,68,68,0.12)' },
}

function StatusPill({ status }) {
  const s = STATUS[status]
  if (!s) return null
  const busy = status === 'indexing' || status === 'uploading'
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-1.5 py-px text-[9px] font-medium tracking-wide"
      style={{ color: s.color, background: s.bg }}
    >
      {busy
        ? <Loader2 className="w-2 h-2 animate-spin" />
        : <span className={cn('w-1 h-1 rounded-full', status === 'ready' && 'pulse-dot')} style={{ background: s.color }} />}
      {s.label}
    </span>
  )
}

/** Rich document card for the right sidebar. */
export function FileCard({ file, onPreview, onRemove, onReindex, onCancelIndexing }) {
  const { Icon, color } = fileMeta(file.name)
  const busy = file.status === 'indexing' || file.status === 'uploading'
  const pct = file.progress?.total > 0
    ? Math.round((file.progress.current / file.progress.total) * 100)
    : null

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96, transition: { duration: 0.15 } }}
      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
      className={cn(
        'group card-lift relative rounded-xl border px-3 py-2.5',
        file.status === 'ready' && 'cursor-pointer'
      )}
      style={{ background: 'var(--bg-card)', borderColor: 'var(--border-soft)' }}
      onClick={() => file.status === 'ready' && onPreview?.(file.name)}
      role={file.status === 'ready' ? 'button' : undefined}
      tabIndex={file.status === 'ready' ? 0 : undefined}
      onKeyDown={e => { if (e.key === 'Enter' && file.status === 'ready') onPreview?.(file.name) }}
      aria-label={`${file.name} — ${file.status}`}
    >
      <div className="flex items-start gap-2.5">
        <div
          className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: `${color}14`, border: `1px solid ${color}26` }}
        >
          <Icon className="w-4 h-4" style={{ color }} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium truncate" style={{ color: 'var(--text-hi)' }} title={file.name}>
            {file.name}
          </div>
          <div className="flex items-center gap-1.5 mt-1">
            <StatusPill status={file.status} />
            {file.size > 0 && (
              <span className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
                {formatFileSize(file.size)}
              </span>
            )}
          </div>

          {/* Indexing progress */}
          {busy && pct !== null && (
            <div className="mt-2">
              <div className="w-full h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                <motion.div
                  className="h-full rounded-full relative overflow-hidden"
                  style={{ background: 'var(--primary)' }}
                  animate={{ width: `${pct}%` }}
                  transition={{ type: 'spring', stiffness: 120, damping: 24 }}
                >
                  <span
                    className="absolute inset-y-0 w-1/2 -translate-x-full"
                    style={{
                      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent)',
                      animation: 'shimmer 1.6s infinite',
                    }}
                  />
                </motion.div>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-[9px]" style={{ color: 'var(--text-faint)' }}>
                  Page {file.progress.current}/{file.progress.total}
                </span>
                <span className="text-[9px] font-medium" style={{ color: 'var(--accent-1)' }}>{pct}%</span>
              </div>
            </div>
          )}

          {file.status === 'indexing' && (
            <button
              type="button"
              className="text-[10px] mt-1 underline underline-offset-2 transition-colors hover:text-[var(--danger)]"
              style={{ color: 'var(--text-faint)' }}
              onClick={e => { e.stopPropagation(); onCancelIndexing?.(file.name) }}
            >
              Cancel indexing
            </button>
          )}
        </div>

        {/* Hover actions */}
        {file.status === 'ready' && (
          <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity flex-shrink-0">
            <IconAction title="Preview" onClick={e => { e.stopPropagation(); onPreview?.(file.name) }}>
              <Eye className="w-3 h-3" />
            </IconAction>
            <IconAction title="Re-index" onClick={e => { e.stopPropagation(); onReindex?.(file.name) }}>
              <RotateCcw className="w-3 h-3" />
            </IconAction>
            <IconAction title="Remove" danger onClick={e => { e.stopPropagation(); onRemove?.(file.name) }}>
              <X className="w-3 h-3" />
            </IconAction>
          </div>
        )}
      </div>
    </motion.div>
  )
}

function IconAction({ children, title, danger, onClick }) {
  return (
    <motion.button
      type="button"
      whileHover={{ scale: 1.12 }}
      whileTap={{ scale: 0.9 }}
      title={title}
      aria-label={title}
      onClick={onClick}
      className="p-1.5 rounded-sm transition-colors"
      style={{ color: 'var(--text-lo)' }}
      onMouseEnter={e => { e.currentTarget.style.color = danger ? 'var(--danger)' : 'var(--text-hi)'; e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
      onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-lo)'; e.currentTarget.style.background = 'transparent' }}
    >
      {children}
    </motion.button>
  )
}

/** Compact file chip shown above the composer. */
export function FileChip({ file, onPreview, onRemove }) {
  const { Icon, color } = fileMeta(file.name)
  const busy = file.status === 'indexing' || file.status === 'uploading'
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 420, damping: 28 }}
      className="glass-subtle group/chip flex items-center gap-1.5 pl-2 pr-1.5 py-1 rounded-full text-xs max-w-[200px]"
      style={{ color: 'var(--text-lo)' }}
      title={file.name}
    >
      {busy
        ? <Loader2 className="w-3 h-3 flex-shrink-0 animate-spin" style={{ color: 'var(--warning)' }} />
        : <Icon className="w-3 h-3 flex-shrink-0" style={{ color }} />}
      <span
        className={cn('truncate', file.status === 'ready' && 'cursor-pointer hover:text-[var(--text-hi)] transition-colors')}
        onClick={() => file.status === 'ready' && onPreview?.(file.name)}
      >
        {file.name}
      </span>
      {busy && <span className="text-[9px] flex-shrink-0" style={{ color: 'var(--warning)' }}>indexing</span>}
      <button
        type="button"
        aria-label={`Remove ${file.name}`}
        className="flex-shrink-0 rounded-full p-0.5 opacity-0 group-hover/chip:opacity-100 transition-all hover:bg-white/10"
        onClick={e => { e.stopPropagation(); onRemove?.(file.name) }}
      >
        <X className="w-2.5 h-2.5" />
      </button>
    </motion.div>
  )
}

export default FileCard
