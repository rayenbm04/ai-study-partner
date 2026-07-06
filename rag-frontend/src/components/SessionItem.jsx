import { motion } from 'framer-motion'
import { MessageSquare, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Chat session row with active indicator, hover glow and delete action. */
export function SessionItem({ session, active, excerpt, onSelect, onDelete }) {
  const msgCount = session.history.filter(h => h.answer).length

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -8, transition: { duration: 0.12 } }}
      transition={{ type: 'spring', stiffness: 400, damping: 32 }}
      className="relative"
    >
      {active && (
        <motion.span
          layoutId="session-active-bar"
          className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-[60%] rounded-full"
          style={{ background: 'var(--primary)' }}
          transition={{ type: 'spring', stiffness: 420, damping: 34 }}
        />
      )}
      <button
        type="button"
        onClick={onSelect}
        aria-current={active ? 'true' : undefined}
        className={cn(
          'w-full text-left rounded-lg pl-3.5 pr-2 py-2.5 group transition-all duration-200 relative overflow-hidden',
          active ? '' : 'hover:bg-white/[0.04]'
        )}
        style={active ? { background: 'color-mix(in srgb, var(--primary) 9%, transparent)' } : undefined}
      >
        <div className="flex items-start justify-between gap-1.5">
          <div className="flex-1 min-w-0">
            <div
              className="text-xs font-medium truncate transition-colors"
              style={{ color: active ? 'var(--text-hi)' : 'var(--text-lo)' }}
            >
              {session.name}
            </div>
            {excerpt ? (
              <div className="text-[10px] truncate mt-0.5" style={{ color: 'var(--text-faint)' }}>{excerpt}</div>
            ) : (
              <div className="flex items-center gap-1 text-[10px] mt-0.5" style={{ color: 'var(--text-faint)' }}>
                <MessageSquare className="w-2.5 h-2.5" />
                {msgCount} · {session.fileNames.length} file{session.fileNames.length !== 1 ? 's' : ''}
              </div>
            )}
          </div>
          <motion.span
            role="button"
            tabIndex={0}
            aria-label={`Delete chat ${session.name}`}
            whileHover={{ scale: 1.15 }}
            whileTap={{ scale: 0.85 }}
            className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity p-1 rounded-md flex-shrink-0 mt-0.5 hover:bg-white/10"
            style={{ color: 'var(--text-faint)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--danger)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-faint)')}
            onClick={ev => { ev.stopPropagation(); onDelete?.() }}
            onKeyDown={ev => { if (ev.key === 'Enter') { ev.stopPropagation(); onDelete?.() } }}
          >
            <Trash2 className="w-3 h-3" />
          </motion.span>
        </div>
      </button>
    </motion.div>
  )
}

export default SessionItem
