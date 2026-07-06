const NOISE_URI =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E\")"

// Generated once at module load so renders stay pure.
const PARTICLES = Array.from({ length: 18 }, (_, i) => ({
  id: i,
  left: `${Math.random() * 100}%`,
  top: `${Math.random() * 100}%`,
  size: 1 + Math.random() * 2,
  duration: `${7 + Math.random() * 9}s`,
  delay: `${-Math.random() * 10}s`,
  opacity: 0.12 + Math.random() * 0.25,
  cyan: i % 4 === 0,
}))

/**
 * Ambient app background: radial gradients, drifting glow blobs,
 * faint grid, noise texture and floating particles.
 * Purely decorative — pointer-events disabled, aria-hidden.
 */
export function Background() {
  return (
    <div aria-hidden="true" className="fixed inset-0 overflow-hidden pointer-events-none select-none" style={{ zIndex: 0 }}>
      {/* Base radial washes */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse 80% 55% at 18% -10%, rgba(124,92,255,0.10), transparent 60%),' +
            'radial-gradient(ellipse 70% 50% at 85% 110%, rgba(76,201,240,0.07), transparent 60%),' +
            'radial-gradient(ellipse 45% 40% at 50% 45%, rgba(124,92,255,0.04), transparent 70%)',
        }}
      />

      {/* Drifting glow blobs */}
      <div
        className="blob-1 absolute rounded-full"
        style={{
          width: 560, height: 560, top: '-14%', left: '-8%',
          background: 'radial-gradient(circle, rgba(124,92,255,0.13), transparent 65%)',
          filter: 'blur(70px)',
        }}
      />
      <div
        className="blob-2 absolute rounded-full"
        style={{
          width: 640, height: 640, bottom: '-22%', right: '-10%',
          background: 'radial-gradient(circle, rgba(76,201,240,0.09), transparent 65%)',
          filter: 'blur(80px)',
        }}
      />
      <div
        className="blob-3 absolute rounded-full"
        style={{
          width: 420, height: 420, top: '38%', left: '42%',
          background: 'radial-gradient(circle, rgba(124,92,255,0.06), transparent 65%)',
          filter: 'blur(90px)',
        }}
      />

      {/* Faint grid, masked toward center */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),' +
            'linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)',
          backgroundSize: '56px 56px',
          maskImage: 'radial-gradient(ellipse 90% 80% at 50% 30%, black 30%, transparent 75%)',
          WebkitMaskImage: 'radial-gradient(ellipse 90% 80% at 50% 30%, black 30%, transparent 75%)',
        }}
      />

      {/* Noise */}
      <div className="absolute inset-0" style={{ backgroundImage: NOISE_URI, opacity: 0.022 }} />

      {/* Floating particles */}
      {PARTICLES.map(p => (
        <span
          key={p.id}
          className="particle absolute rounded-full"
          style={{
            left: p.left,
            top: p.top,
            width: p.size,
            height: p.size,
            background: p.cyan ? 'rgba(76,201,240,0.9)' : 'rgba(124,92,255,0.9)',
            '--p-op': p.opacity,
            '--p-dur': p.duration,
            animationDelay: p.delay,
          }}
        />
      ))}

      {/* Bottom vignette to anchor the composer */}
      <div
        className="absolute inset-x-0 bottom-0 h-48"
        style={{ background: 'linear-gradient(to top, rgba(9,9,11,0.9), transparent)' }}
      />
    </div>
  )
}

export default Background
