/** Elegant three-dot typing indicator with optional label. */
export function TypingIndicator({ label }) {
  return (
    <div className="flex items-center gap-2.5" role="status" aria-live="polite">
      <div className="flex items-center gap-1">
        {[0, 1, 2].map(i => (
          <span
            key={i}
            className="typing-dot w-1.5 h-1.5 rounded-full"
            style={{ background: 'var(--accent-1)', animationDelay: `${i * 0.18}s` }}
          />
        ))}
      </div>
      {label && <span className="text-xs" style={{ color: 'var(--text-lo)' }}>{label}</span>}
    </div>
  )
}

export default TypingIndicator
