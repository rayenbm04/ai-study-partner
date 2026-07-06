import { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import {
  Plus, Search, Upload, FileText, X, Square, BarChart2, LogOut, Link2,
  ChevronDown, ChevronUp, AlertTriangle, Copy, Check, Loader2, ExternalLink,
  BookOpen, MessageSquare, PanelLeftClose, PanelLeft, PanelRightClose,
  PanelRight, Printer, Cpu, Cloud,
} from 'lucide-react'
import { AreaChart, Area, XAxis, Tooltip as RechartTooltip, ResponsiveContainer } from 'recharts'
import { BackgroundBeams } from '@/components/ui/background-beams'
import { Spotlight } from '@/components/ui/spotlight'
import { TextGenerateEffect } from '@/components/ui/text-generate-effect'
import { HoverEffect } from '@/components/ui/card-hover-effect'
import { TypingIndicator } from '@/components/TypingIndicator'
import { Markdown } from '@/components/Markdown'
import { Composer } from '@/components/Composer'
import { SessionItem } from '@/components/SessionItem'
import { FileCard, fileMeta } from '@/components/FileCard'
import './App.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const COST_MODELS = [
  { name: 'GPT-4o',           input: 2.50,  output: 10.00 },
  { name: 'GPT-4o mini',      input: 0.15,  output: 0.60  },
  { name: 'Claude Sonnet 4',  input: 3.00,  output: 15.00 },
  { name: 'Claude Haiku 4',   input: 0.80,  output: 4.00  },
  { name: 'Gemini 1.5 Pro',   input: 1.25,  output: 5.00  },
  { name: 'Gemini 1.5 Flash', input: 0.075, output: 0.30  },
]

const CLOUD_MODELS = [
  { key: 'llama-3.3-70b-versatile',                   label: 'Llama 3.3 70B',   limit: 100_000 },
  { key: 'llama-3.1-8b-instant',                      label: 'Llama 3.1 8B',    limit: 500_000 },
  { key: 'meta-llama/llama-4-scout-17b-16e-instruct', label: 'Llama 4 Scout',   limit: 100_000 },
]

const SPRING = { type: 'spring', stiffness: 320, damping: 34 }

function evalColor(score) {
  if (score >= 0.8) return 'var(--success)'
  if (score >= 0.5) return 'var(--warning)'
  return 'var(--danger)'
}
function generateId() {
  return Math.random().toString(36).substring(2, 9)
}
function createNewSession() {
  return { id: generateId(), name: 'New chat', createdAt: new Date().toISOString(), fileNames: [], history: [] }
}

// ─── Small shared bits ───────────────────────────────────────────────────────

function GhostIconButton({ title, onClick, children, className }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <motion.button
          type="button"
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.9 }}
          aria-label={title}
          onClick={onClick}
          className={cn('h-8 w-8 rounded-sm flex items-center justify-center transition-colors hover:bg-white/[0.06]', className)}
          style={{ color: 'var(--text-lo)' }}
        >
          {children}
        </motion.button>
      </TooltipTrigger>
      <TooltipContent>{title}</TooltipContent>
    </Tooltip>
  )
}

function LogoMark({ size = 'md' }) {
  const dim = size === 'lg' ? 'w-12 h-12 rounded-md' : 'w-7 h-7 rounded-sm'
  const icon = size === 'lg' ? 'w-6 h-6' : 'w-3.5 h-3.5'
  return (
    <div
      className={cn(dim, 'flex items-center justify-center flex-shrink-0')}
      style={{ background: 'var(--primary)' }}
    >
      <MessageSquare className={cn(icon, 'text-white')} />
    </div>
  )
}

function CopyButton({ text, className }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      aria-label="Copy"
      className={cn('flex items-center gap-1 text-[10px] transition-colors', className)}
      style={{ color: copied ? 'var(--success)' : 'var(--text-faint)' }}
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 1600)
      }}
    >
      {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

// ─── Auth Screen ────────────────────────────────────────────────────────────

function AuthScreen({ onAuth }) {
  const [view, setView]           = useState('login')
  const [email, setEmail]         = useState('')
  const [password, setPassword]   = useState('')
  const [firstname, setFirstname] = useState('')
  const [lastname, setLastname]   = useState('')
  const [error, setError]         = useState('')
  const [loading, setLoading]     = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      const res = await fetch(`${API}/auth/${view}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(view === 'register'
          ? { email, password, firstname, lastname }
          : { email, password }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || 'Error'); return }
      localStorage.setItem('rag_token', data.access_token)
      localStorage.setItem('rag_user', JSON.stringify(data.user))
      onAuth(data.access_token, data.user)
    } catch { setError('Cannot reach server') }
    finally { setLoading(false) }
  }

  const inputCls = 'h-10 rounded-md text-sm bg-white/[0.04] border-white/[0.08] focus-visible:ring-1 focus-visible:ring-[var(--primary)] placeholder:text-[var(--text-faint)]'

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden" style={{ background: 'var(--bg-base)' }}>
      <BackgroundBeams className="opacity-40" />
      <motion.div
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ ...SPRING, delay: 0.05 }}
        className="glass-strong w-full max-w-sm rounded-xl relative z-10 p-8"
      >
        <div className="text-center mb-7">
          <motion.div
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ ...SPRING, delay: 0.15 }}
            className="mx-auto mb-4 w-fit"
          >
            <LogoMark size="lg" />
          </motion.div>
          <h1 className="text-xl font-semibold tracking-tight">RAG Assistant</h1>
          <p className="text-xs mt-1.5" style={{ color: 'var(--text-lo)' }}>
            {view === 'login' ? 'Welcome back — sign in to continue' : 'Create your account'}
          </p>
        </div>

        {/* Segmented switch */}
        <div
          className="flex rounded-md p-1 mb-6 gap-1"
          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-soft)' }}
          role="tablist"
        >
          {['login', 'register'].map(v => (
            <button
              key={v}
              role="tab"
              aria-selected={view === v}
              onClick={() => { setView(v); setError('') }}
              className="relative flex-1 py-1.5 text-xs rounded-sm font-medium transition-colors"
              style={{ color: view === v ? 'var(--text-hi)' : 'var(--text-faint)' }}
            >
              {view === v && (
                <motion.span
                  layoutId="auth-tab"
                  className="absolute inset-0 rounded-sm"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-med)' }}
                  transition={{ type: 'spring', stiffness: 500, damping: 36 }}
                />
              )}
              <span className="relative z-10">{v === 'login' ? 'Sign in' : 'Register'}</span>
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="space-y-3">
          <Input className={inputCls} type="email" placeholder="Email" value={email}
            onChange={e => setEmail(e.target.value)} required autoComplete="email" />
          <Input className={inputCls} type="password" placeholder="Password (min 6 chars)" value={password}
            onChange={e => setPassword(e.target.value)} required autoComplete="current-password" />
          <AnimatePresence>
            {view === 'register' && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-3 overflow-hidden"
              >
                <Input className={inputCls} type="text" placeholder="First name" value={firstname}
                  onChange={e => setFirstname(e.target.value)} required={view === 'register'} />
                <Input className={inputCls} type="text" placeholder="Last name" value={lastname}
                  onChange={e => setLastname(e.target.value)} required={view === 'register'} />
              </motion.div>
            )}
          </AnimatePresence>
          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="text-xs px-3 py-2 rounded-lg"
                style={{ color: 'var(--danger)', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)' }}
                role="alert"
              >
                {error}
              </motion.p>
            )}
          </AnimatePresence>
          <motion.button
            type="submit"
            disabled={loading}
            whileHover={{ scale: 1.015 }}
            whileTap={{ scale: 0.985 }}
            className="w-full h-10 rounded-sm text-sm font-medium text-white flex items-center justify-center gap-2 disabled:opacity-60"
            style={{ background: 'var(--primary)' }}
          >
            {loading
              ? <><Loader2 className="w-4 h-4 animate-spin" />Please wait…</>
              : view === 'login' ? 'Sign in' : 'Create account'}
          </motion.button>
        </form>

        <p className="text-center text-[11px] mt-5" style={{ color: 'var(--text-faint)' }}>
          {view === 'login' ? 'First account becomes admin. ' : 'Already have an account? '}
          <button
            onClick={() => { setView(view === 'login' ? 'register' : 'login'); setError('') }}
            className="font-medium hover:underline underline-offset-2"
            style={{ color: 'var(--accent-1)' }}
          >
            {view === 'login' ? 'Register' : 'Sign in'}
          </button>
        </p>
      </motion.div>
    </div>
  )
}

// ─── Main App ────────────────────────────────────────────────────────────────

function MainApp({ authFetch, currentUser, onLogout }) {
  const sessionsKey = `rag-sessions-${currentUser.id}`
  const activeKey   = `rag-active-session-${currentUser.id}`

  // ── State ─────────────────────────────────────────────────────────────────
  const [sessions, setSessions] = useState(() => {
    try {
      const saved = localStorage.getItem(sessionsKey)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed) && parsed.length > 0) return parsed
      }
    } catch {}
    return [createNewSession()]
  })
  const [activeSessionId, setActiveSessionId] = useState(() => {
    try { return localStorage.getItem(activeKey) } catch { return null }
  })
  const [globalFiles, setGlobalFiles]         = useState({})
  const [question, setQuestion]               = useState('')
  const [isLoading, setIsLoading]             = useState(false)
  const [streamMode, setStreamMode]           = useState(true)
  const [isDragOver, setIsDragOver]           = useState(false)
  const [showPromptNav, setShowPromptNav]     = useState(false)
  const [showScrollDown, setShowScrollDown]   = useState(false)
  const [showDashboard, setShowDashboard]     = useState(false)
  const [dashboardData, setDashboardData]     = useState(null)
  const [evalData, setEvalData]               = useState(null)
  const [evalLoading, setEvalLoading]         = useState(false)
  const [chunkView, setChunkView]             = useState({})
  const [summaryView, setSummaryView]         = useState({})
  const [evalSelectedQ, setEvalSelectedQ]     = useState(null)
  const [qualityData, setQualityData]         = useState(null)
  const [qualityLoading, setQualityLoading]   = useState(false)
  const [qualitySelectedQ, setQualitySelectedQ] = useState(null)
  const [urlInput, setUrlInput]               = useState('')
  const [urlLoading, setUrlLoading]           = useState(false)
  const [urlError, setUrlError]               = useState('')
  const [sessionSearch, setSessionSearch]     = useState('')
  const [selectedCostModel, setSelectedCostModel] = useState('GPT-4o')
  const [tokenStats, setTokenStats]           = useState(null)
  const [previewFile, setPreviewFile]         = useState(null)
  const [previewBlobUrl, setPreviewBlobUrl]   = useState(null)
  const [previewText, setPreviewText]         = useState(null)
  const [provider, setProvider]               = useState(() => localStorage.getItem('rag-provider') || 'local')
  const [groqTokens, setGroqTokens]           = useState(null)
  const [showLeftSidebar, setShowLeftSidebar] = useState(() => {
    const saved = localStorage.getItem('rag-left-sidebar')
    if (saved !== null) return saved === 'true'
    return window.innerWidth >= 900
  })
  const [showRightSidebar, setShowRightSidebar] = useState(() => {
    const saved = localStorage.getItem('rag-right-sidebar')
    if (saved !== null) return saved === 'true'
    return window.innerWidth >= 1280
  })
  const [cloudModel, setCloudModel] = useState(() => localStorage.getItem('rag-cloud-model') || 'llama-3.3-70b-versatile')
  const [rightSidebarTab, setRightSidebarTab] = useState('files')
  const [usagePeriod, setUsagePeriod] = useState('daily')
  const [hypothesisOpenId, setHypothesisOpenId] = useState(null)
  const [showChatUrl, setShowChatUrl] = useState(false)
  const [chatUrlInput, setChatUrlInput] = useState('')
  const [showAllModels, setShowAllModels] = useState(false)

  // ── Refs ──────────────────────────────────────────────────────────────────
  const fileInputRef       = useRef(null)
  const chatEndRef         = useRef(null)
  const chatScrollRef      = useRef(null)
  const abortControllerRef = useRef(null)
  const scrollTimerRef     = useRef(null)
  const pendingIdRef       = useRef(null)
  const isLoadingRef       = useRef(false)
  const currentQuestionRef = useRef('')
  const pollingRef         = useRef({})
  const historyRef         = useRef([])
  const historyIndexRef    = useRef(-1)
  const draftQuestionRef   = useRef('')
  const searchInputRef     = useRef(null)

  // ── Derived ───────────────────────────────────────────────────────────────
  const activeSession    = sessions.find(s => s.id === activeSessionId) || sessions[0]
  const history          = activeSession?.history    || []
  const sessionFileNames = activeSession?.fileNames  || []
  const sessionFiles     = sessionFileNames.map(name => ({
    name, id: name,
    status:   globalFiles[name]?.status   || 'ready',
    size:     globalFiles[name]?.size     || 0,
    progress: globalFiles[name]?.progress || null,
  }))
  const anyIndexing = sessionFiles.some(f => f.status === 'indexing' || f.status === 'uploading')
  const streamingId = isLoading && history.length > 0 ? history[history.length - 1].id : null

  const evalEntries     = sessions.flatMap(s => s.history.filter(e => e.eval))
  const avgFaithfulness = evalEntries.length
    ? evalEntries.reduce((a, e) => a + e.eval.faithfulness, 0) / evalEntries.length : null
  const avgRelevance    = evalEntries.length
    ? evalEntries.reduce((a, e) => a + e.eval.answer_relevance, 0) / evalEntries.length : null
  const totalQuestions  = sessions.reduce((acc, s) => acc + s.history.filter(e => e.answer !== null).length, 0)

  // ── Effects ───────────────────────────────────────────────────────────────
  useEffect(() => { historyRef.current = history }, [history])

  useEffect(() => {
    document.documentElement.classList.add('dark')
    document.documentElement.setAttribute('data-theme', 'dark')
  }, [])

  useEffect(() => { localStorage.setItem('rag-cloud-model', cloudModel) }, [cloudModel])
  useEffect(() => { localStorage.setItem('rag-left-sidebar', String(showLeftSidebar)) }, [showLeftSidebar])
  useEffect(() => { localStorage.setItem('rag-right-sidebar', String(showRightSidebar)) }, [showRightSidebar])

  useEffect(() => {
    if (!showDashboard) return
    authFetch(`${API}/dashboard`).then(r => r.json()).then(d => {
      setDashboardData(d); setTokenStats(d.tokens); if (d.groq_tokens) setGroqTokens(d.groq_tokens)
    }).catch(() => {})
  }, [provider, cloudModel, showDashboard])

  useEffect(() => {
    localStorage.setItem('rag-provider', provider)
    const token = localStorage.getItem('rag_token')
    if (!token) return
    fetch(`${API}/provider`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ provider }),
    }).catch(() => {})
  }, [provider])

  useEffect(() => { localStorage.setItem(sessionsKey, JSON.stringify(sessions)) }, [sessions])
  useEffect(() => {
    if (activeSession?.id) localStorage.setItem(activeKey, activeSession.id)
  }, [activeSession?.id])

  useEffect(() => {
    authFetch(`${API}/dashboard`).then(r => r.json()).then(d => {
      setTokenStats(d.tokens)
      if (d.groq_tokens) setGroqTokens(d.groq_tokens)
    }).catch(() => {})
  }, [authFetch])

  useEffect(() => {
    authFetch(`${API}/documents`)
      .then(r => r.json())
      .then(docs => {
        const registry = {}
        docs.forEach(d => { registry[d.name] = { status: d.status || 'ready', size: 0 } })
        setGlobalFiles(registry)
      }).catch(() => {})
  }, [authFetch])

  useEffect(() => {
    if (!previewFile) {
      if (previewBlobUrl) { URL.revokeObjectURL(previewBlobUrl); setPreviewBlobUrl(null) }
      setPreviewText(null)
      return
    }
    const ext = previewFile.split('.').pop().toLowerCase()
    const isPreviewable = ['pdf','png','jpg','jpeg','gif','bmp','webp'].includes(ext)
    const isPptx        = ext === 'pptx'
    const isDocPreview  = ['docx','doc','xlsx','xls'].includes(ext)
    const isTextPreview = ['puml','plantuml','uml','txt','md','csv'].includes(ext)

    if (isPreviewable) {
      authFetch(`${API}/files/${encodeURIComponent(previewFile)}`)
        .then(r => r.blob()).then(blob => setPreviewBlobUrl(URL.createObjectURL(blob)))
        .catch(() => setPreviewBlobUrl(null))
    } else if (isPptx) {
      authFetch(`${API}/slides-pdf/${encodeURIComponent(previewFile)}`)
        .then(r => { if (!r.ok) return r.json().then(d => Promise.reject(d.detail || 'Conversion failed')); return r.blob() })
        .then(blob => setPreviewBlobUrl(URL.createObjectURL(blob)))
        .catch(err => setPreviewText(typeof err === 'string' ? err : 'Could not convert to PDF'))
    } else if (isDocPreview) {
      authFetch(`${API}/doc-pdf/${encodeURIComponent(previewFile)}`)
        .then(r => { if (!r.ok) return r.json().then(d => Promise.reject(d.detail || 'Conversion failed')); return r.blob() })
        .then(blob => setPreviewBlobUrl(URL.createObjectURL(blob)))
        .catch(err => setPreviewText(typeof err === 'string' ? err : 'Could not convert to PDF'))
    } else if (isTextPreview) {
      authFetch(`${API}/preview/${encodeURIComponent(previewFile)}`)
        .then(r => r.json()).then(d => setPreviewText(d.text || ''))
        .catch(() => setPreviewText('[Could not load preview]'))
    }
    return () => {
      setPreviewBlobUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null })
      setPreviewText(null)
    }
  }, [previewFile, authFetch])

  useEffect(() => {
    const el = chatScrollRef.current
    if (!el) return
    const onScroll = () => setShowScrollDown(el.scrollHeight - el.scrollTop - el.clientHeight > 120)
    el.addEventListener('scroll', onScroll)
    return () => el.removeEventListener('scroll', onScroll)
  }, [history.length === 0])

  useEffect(() => () => Object.values(pollingRef.current).forEach(clearInterval), [])

  useEffect(() => {
    if (!tokenStats?.total || !currentUser?.email) return
    const today = new Date().toISOString().slice(0, 10)
    const key = `rag-usage-${currentUser.email}`
    try {
      const saved = JSON.parse(localStorage.getItem(key) || '{}')
      saved[today] = { prompt: tokenStats.prompt || 0, completion: tokenStats.completion || 0, total: tokenStats.total }
      localStorage.setItem(key, JSON.stringify(saved))
    } catch {}
  }, [tokenStats, currentUser?.email])


  // ── Callbacks ─────────────────────────────────────────────────────────────
  const updateHistory = useCallback((updater) => {
    const sid = activeSession?.id
    setSessions(prev => prev.map(s =>
      s.id === sid
        ? { ...s, history: typeof updater === 'function' ? updater(s.history) : updater }
        : s
    ))
  }, [activeSession?.id])

  const createSession = useCallback(() => {
    if (activeSession && activeSession.history.length === 0 && activeSession.fileNames.length === 0) {
      setActiveSessionId(activeSession.id); return
    }
    const s = createNewSession()
    setSessions(prev => [s, ...prev])
    setActiveSessionId(s.id)
    setQuestion('')
  }, [activeSession])

  // Keyboard shortcuts
  useEffect(() => {
    const onKey = (e) => {
      const mod = e.metaKey || e.ctrlKey
      if (!mod) return
      if (e.key.toLowerCase() === 'b' && !e.shiftKey) { e.preventDefault(); setShowLeftSidebar(p => !p) }
      if (e.key.toLowerCase() === 'b' && e.shiftKey)  { e.preventDefault(); setShowRightSidebar(p => !p) }
      if (e.key.toLowerCase() === 'o' && e.shiftKey)  { e.preventDefault(); createSession() }
      if (e.key.toLowerCase() === 'k') { e.preventDefault(); setShowLeftSidebar(true); setTimeout(() => searchInputRef.current?.focus(), 60) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [createSession])

  const switchSession = useCallback((id) => {
    if (isLoadingRef.current) {
      const cancelledId = pendingIdRef.current
      pendingIdRef.current = null; isLoadingRef.current = false; setIsLoading(false)
      if (abortControllerRef.current) { abortControllerRef.current.abort(); abortControllerRef.current = null }
      if (cancelledId) setSessions(prev => prev.map(s => ({ ...s, history: s.history.filter(e => e.id !== cancelledId) })))
    }
    setActiveSessionId(id); setQuestion('')
    historyIndexRef.current = -1; draftQuestionRef.current = ''
  }, [])

  const deleteSession = useCallback((id) => {
    setSessions(prev => {
      const target    = prev.find(s => s.id === id)
      const remaining = prev.filter(s => s.id !== id)
      if (target?.fileNames?.length) {
        const otherFiles = new Set(remaining.flatMap(s => s.fileNames))
        target.fileNames.forEach(filename => {
          if (!otherFiles.has(filename)) {
            authFetch(`${API}/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' })
              .then(() => setGlobalFiles(prev => { const n = { ...prev }; delete n[filename]; return n }))
              .catch(e => console.error('Delete file on session removal failed:', e))
          }
        })
      }
      if (remaining.length === 0) {
        const fresh = createNewSession(); setActiveSessionId(fresh.id); return [fresh]
      }
      if (activeSession?.id === id) setActiveSessionId(remaining[0].id)
      return remaining
    })
  }, [activeSession?.id, authFetch])

  const addFileToSession = useCallback((filename) => {
    const sid = activeSession?.id
    setSessions(prev => prev.map(s => {
      if (s.id !== sid || s.fileNames.includes(filename)) return s
      const shouldRename  = s.name === 'New chat' && s.history.length === 0
      const nameFromFile  = filename.replace(/\.[^/.]+$/, '')
      const name = shouldRename ? (nameFromFile.length > 35 ? nameFromFile.slice(0, 35) + '…' : nameFromFile) : s.name
      return { ...s, name, fileNames: [...s.fileNames, filename] }
    }))
  }, [activeSession?.id])

  const handleInputKeyDown = useCallback((e) => {
    if (isLoadingRef.current) return
    const completed = historyRef.current.filter(h => h.answer !== null)
    if (completed.length === 0) return
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (historyIndexRef.current === -1) draftQuestionRef.current = e.target.value
      const next = Math.min(historyIndexRef.current + 1, completed.length - 1)
      historyIndexRef.current = next
      setQuestion(completed[completed.length - 1 - next].question)
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIndexRef.current === -1) return
      const next = historyIndexRef.current - 1
      historyIndexRef.current = next
      setQuestion(next === -1 ? draftQuestionRef.current : completed[completed.length - 1 - next].question)
    }
  }, [])

  const scrollToBottom = useCallback(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const pollStatus = useCallback((filename) => {
    if (pollingRef.current[filename]) return
    pollingRef.current[filename] = setInterval(async () => {
      try {
        const res  = await authFetch(`${API}/status/${encodeURIComponent(filename)}`)
        const data = await res.json()
        if (data.status === 'ready' || data.status === 'error') {
          clearInterval(pollingRef.current[filename]); delete pollingRef.current[filename]
          setGlobalFiles(prev => ({ ...prev, [filename]: { ...prev[filename], status: data.status, progress: null } }))
        } else {
          setGlobalFiles(prev => ({ ...prev, [filename]: { ...prev[filename], status: data.status, progress: data.progress || null } }))
        }
      } catch { clearInterval(pollingRef.current[filename]); delete pollingRef.current[filename] }
    }, 2000)
  }, [authFetch])

  const uploadToBackend = useCallback(async (file) => {
    const fd = new FormData(); fd.append('file', file)
    const res = await authFetch(`${API}/upload`, { method: 'POST', body: fd })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  }, [authFetch])

  const handleFileSelect = useCallback(async (selectedFiles) => {
    const valid = Array.from(selectedFiles).filter(f => {
      const ext = f.name.split('.').pop().toLowerCase()
      return f.type === 'application/pdf' || f.type.startsWith('image/') ||
        f.type === 'text/plain' || ext === 'txt' || ext === 'docx' ||
        f.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
        ext === 'xlsx' || ext === 'xls' ||
        f.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
        f.type === 'application/vnd.ms-excel' ||
        ext === 'puml' || ext === 'plantuml' || ext === 'uml' ||
        ext === 'md' || ext === 'csv' || ext === 'pptx'
    })
    for (const f of valid) {
      if (globalFiles[f.name]?.status === 'ready') {
        try {
          const check = await authFetch(`${API}/status/${encodeURIComponent(f.name)}`)
          const serverStatus = await check.json()
          if (serverStatus.status === 'ready') { addFileToSession(f.name); continue }
        } catch {}
      }
      if (globalFiles[f.name]?.status === 'indexing') { addFileToSession(f.name); pollStatus(f.name); continue }
      setGlobalFiles(prev => ({ ...prev, [f.name]: { status: 'uploading', size: f.size } }))
      addFileToSession(f.name)
      try {
        const result = await uploadToBackend(f)
        setGlobalFiles(prev => ({ ...prev, [f.name]: { ...prev[f.name], status: result.status } }))
        if (result.status === 'indexing') pollStatus(f.name)
      } catch { setGlobalFiles(prev => ({ ...prev, [f.name]: { ...prev[f.name], status: 'error' } })) }
    }
  }, [globalFiles, addFileToSession, uploadToBackend, pollStatus, authFetch])

  const handleRemoveFile = useCallback(async (filename) => {
    const sid = activeSession?.id
    setSessions(prev => prev.map(s => s.id === sid ? { ...s, fileNames: s.fileNames.filter(n => n !== filename) } : s))
    const otherUses = sessions.some(s => s.id !== sid && s.fileNames.includes(filename))
    if (!otherUses) {
      try {
        await authFetch(`${API}/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' })
        setGlobalFiles(prev => { const n = { ...prev }; delete n[filename]; return n })
      } catch (e) { console.error('Delete failed:', e) }
    }
  }, [activeSession?.id, sessions, authFetch])

  const handleReindexFile = useCallback(async (filename) => {
    setGlobalFiles(prev => ({ ...prev, [filename]: { ...prev[filename], status: 'indexing' } }))
    try {
      await authFetch(`${API}/reindex/${encodeURIComponent(filename)}`, { method: 'POST' })
      pollStatus(filename)
    } catch (e) {
      console.error('Re-index failed:', e)
      setGlobalFiles(prev => ({ ...prev, [filename]: { ...prev[filename], status: 'error' } }))
    }
  }, [authFetch, pollStatus])

  const handleCancelIndexing = useCallback(async (filename) => {
    try {
      await authFetch(`${API}/cancel/${encodeURIComponent(filename)}`, { method: 'POST' })
      if (pollingRef.current[filename]) { clearInterval(pollingRef.current[filename]); delete pollingRef.current[filename] }
      const sid = activeSession?.id
      setSessions(prev => prev.map(s => s.id === sid ? { ...s, fileNames: s.fileNames.filter(n => n !== filename) } : s))
      setGlobalFiles(prev => { const n = { ...prev }; delete n[filename]; return n })
    } catch (e) { console.error('Cancel failed:', e) }
  }, [activeSession?.id, authFetch])

  const handleUrlIngest = useCallback(async (e, overrideUrl) => {
    if (e?.preventDefault) e.preventDefault()
    const url = (overrideUrl || urlInput).trim(); if (!url) return
    setUrlError(''); setUrlLoading(true)
    try {
      const res  = await authFetch(`${API}/upload-url`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      const data = await res.json()
      if (!res.ok) { setUrlError(data.detail || 'Failed to fetch URL'); return }
      if (!overrideUrl) setUrlInput('')
      setGlobalFiles(prev => ({ ...prev, [data.name]: { status: 'indexing', size: 0 } }))
      addFileToSession(data.name); pollStatus(data.name)
    } catch { setUrlError('Cannot reach server') }
    finally { setUrlLoading(false) }
  }, [urlInput, authFetch, addFileToSession, pollStatus])

  const handleCancel = useCallback((e) => {
    if (e?.preventDefault) e.preventDefault()
    if (scrollTimerRef.current) { clearTimeout(scrollTimerRef.current); scrollTimerRef.current = null }
    const cancelledId = pendingIdRef.current
    pendingIdRef.current = null; isLoadingRef.current = false
    if (cancelledId) {
      setSessions(prev => prev.map(s => ({ ...s, history: s.history.filter(h => h.id !== cancelledId) })))
      setQuestion(currentQuestionRef.current)
    }
    setIsLoading(false)
    if (abortControllerRef.current) { abortControllerRef.current.abort(); abortControllerRef.current = null }
  }, [])

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault()
    if (!question.trim() || isLoadingRef.current) return
    const currentQuestion = question.trim()
    currentQuestionRef.current = currentQuestion
    historyIndexRef.current = -1; draftQuestionRef.current = ''
    isLoadingRef.current = true; setIsLoading(true); setQuestion('')
    abortControllerRef.current = new AbortController()
    const tempId = generateId(); pendingIdRef.current = tempId
    updateHistory(prev => [...prev, { id: tempId, question: currentQuestion, answer: null, sources: [], citations: [], warning: null, sentAt: new Date().toISOString() }])
    scrollTimerRef.current = setTimeout(scrollToBottom, 100)
    const sid = activeSession?.id
    const isFirstMessage = activeSession?.history.length === 0
    try {
      const res = await authFetch(`${API}/ask`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: currentQuestion,
          history: historyRef.current
            .filter(e => e.answer !== null && !e.answer.startsWith('Error:'))
            .map(e => ({ question: e.question, answer: e.answer })),
          files: sessionFileNames, provider,
          groq_model: provider === 'cloud' ? cloudModel : undefined,
          stream: streamMode,
          fast: !streamMode,
        }),
        signal: abortControllerRef.current.signal,
      })
      if (!pendingIdRef.current) return
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || `Server error: ${res.status}`) }

      // ── Instant mode: single JSON response ──────────────────────────────────
      if (!streamMode) {
        const data = await res.json()
        updateHistory(prev => prev.map(entry => entry.id === tempId
          ? { ...entry, answer: (data.answer ?? '').trim(), sources: data.sources || [],
              citations: data.citations || [], warning: data.warning || null, mode: data.mode || 'standard' }
          : entry))
        scrollTimerRef.current = setTimeout(scrollToBottom, 100)
        authFetch(`${API}/dashboard`).then(r => r.json()).then(d => { setTokenStats(d.tokens); if (d.groq_tokens) setGroqTokens(d.groq_tokens) }).catch(() => {})
        if (isFirstMessage) {
          authFetch(`${API}/title`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: currentQuestion, files: sessionFileNames }) })
            .then(r => r.json()).then(({ title }) => { if (title) setSessions(prev => prev.map(s => s.id === sid ? { ...s, name: title } : s)) }).catch(() => {})
        }
        return
      }
      // ── Stream mode: SSE ────────────────────────────────────────────────────
      const reader = res.body.getReader(); const decoder = new TextDecoder()
      let buffer = ''; let scrolledOnFirst = false
      while (true) {
        if (!pendingIdRef.current) { reader.cancel(); break }
        const { done, value } = await reader.read(); if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n'); buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim(); if (!raw) continue
          let data; try { data = JSON.parse(raw) } catch { continue }
          if (data.type === 'token' && data.content) {
            updateHistory(prev => prev.map(entry => entry.id === tempId ? { ...entry, answer: (entry.answer ?? '') + data.content } : entry))
            if (!scrolledOnFirst) { scrolledOnFirst = true; scrollTimerRef.current = setTimeout(scrollToBottom, 100) }
          } else if (data.type === 'done') {
            updateHistory(prev => prev.map(entry => entry.id === tempId
              ? { ...entry, answer: (entry.answer ?? '').trim(), sources: data.sources || [], citations: data.citations || [], warning: data.warning || null, mode: data.mode || 'standard' }
              : entry))
            scrollTimerRef.current = setTimeout(scrollToBottom, 100)
            authFetch(`${API}/dashboard`).then(r => r.json()).then(d => { setTokenStats(d.tokens); if (d.groq_tokens) setGroqTokens(d.groq_tokens) }).catch(() => {})
            if (isFirstMessage) {
              authFetch(`${API}/title`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: currentQuestion, files: sessionFileNames }) })
                .then(r => r.json()).then(({ title }) => { if (title) setSessions(prev => prev.map(s => s.id === sid ? { ...s, name: title } : s)) }).catch(() => {})
            }
          } else if (data.type === 'indexing_wait') {
            updateHistory(prev => prev.map(entry => entry.id === tempId ? { ...entry, indexingWait: true } : entry))
          } else if (data.type === 'hypothesis') {
            updateHistory(prev => prev.map(entry => entry.id === tempId ? { ...entry, hypothesis: data.text, indexingWait: false } : entry))
          } else if (data.type === 'eval') {
            setSessions(prev => prev.map(s => ({ ...s, history: s.history.map(entry => entry.id === tempId ? { ...entry, eval: { faithfulness: data.faithfulness, answer_relevance: data.answer_relevance } } : entry) })))
          } else if (data.type === 'error') { throw new Error(data.message) }
        }
      }
    } catch (err) {
      if (!pendingIdRef.current) return
      setQuestion(currentQuestionRef.current)
      const msg = err.message || ''
      const isRateLimit  = msg.toLowerCase().includes('rate limit')
      const isDailyLimit = isRateLimit && (msg.toLowerCase().includes('per day') || msg.toLowerCase().includes('tpd') || msg.toLowerCase().includes('tomorrow'))
      updateHistory(prev => prev.map(entry => entry.id === tempId
        ? { ...entry, answer: isRateLimit ? '' : `Error: ${msg}`, rateLimitError: isRateLimit, rateLimitDaily: isDailyLimit }
        : entry))
      authFetch(`${API}/dashboard`).then(r => r.json()).then(d => { setTokenStats(d.tokens); if (d.groq_tokens) setGroqTokens(d.groq_tokens) }).catch(() => {})
    } finally {
      if (pendingIdRef.current === tempId) {
        pendingIdRef.current = null; isLoadingRef.current = false; setIsLoading(false); abortControllerRef.current = null
      }
    }
  }, [question, scrollToBottom, updateHistory, sessionFileNames, activeSession, authFetch, provider, cloudModel, streamMode])

  const openDashboard = useCallback(async () => {
    setShowDashboard(true); setEvalData(null); setChunkView({}); setSummaryView({})
    try { const res = await authFetch(`${API}/dashboard`); setDashboardData(await res.json()) }
    catch { setDashboardData(null) }
  }, [authFetch])

  const runEval = useCallback(async () => {
    setEvalLoading(true); setEvalData(null)
    try {
      const res  = await authFetch(`${API}/eval`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Eval failed')
      setEvalData(data)
    } catch (e) { setEvalData({ error: e.message }) }
    finally { setEvalLoading(false) }
  }, [authFetch])

  const runQualityEval = useCallback(async () => {
    setQualityLoading(true); setQualityData(null)
    try {
      const params = new URLSearchParams({ provider })
      if (provider === 'cloud') params.set('groq_model', cloudModel)
      const res  = await authFetch(`${API}/eval/quality?${params}`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Quality eval failed')
      setQualityData(data)
    } catch (e) { setQualityData({ error: e.message }) }
    finally { setQualityLoading(false) }
  }, [authFetch, provider, cloudModel])

  // ── Session list (derived) ─────────────────────────────────────────────────
  const q = sessionSearch.trim().toLowerCase()
  const visibleSessions = q
    ? sessions.filter(s => s.name.toLowerCase().includes(q) || s.history.some(e => e.question?.toLowerCase().includes(q) || e.answer?.toLowerCase().includes(q)))
    : sessions
  const excerptFor = (s) => {
    if (!q) return null
    const match = s.history.find(e => e.question?.toLowerCase().includes(q) || e.answer?.toLowerCase().includes(q))
    if (!match) return null
    const src = match.question?.toLowerCase().includes(q) ? match.question : match.answer
    const idx = src.toLowerCase().indexOf(q)
    const start = Math.max(0, idx - 20)
    return (start > 0 ? '…' : '') + src.slice(start, idx + q.length + 35).trim() + '…'
  }

  // ── Composer (shared between empty + active states) ───────────────────────
  const composerEl = (
    <Composer
      value={question}
      onChange={setQuestion}
      onSubmit={handleSubmit}
      onHistoryKey={handleInputKeyDown}
      isLoading={isLoading}
      onCancel={handleCancel}
      streamMode={streamMode}
      onToggleStream={() => setStreamMode(p => !p)}
      onAttach={() => fileInputRef.current?.click()}
      showUrl={showChatUrl}
      onToggleUrl={() => { setShowChatUrl(p => !p); setChatUrlInput('') }}
      urlValue={chatUrlInput}
      onUrlChange={setChatUrlInput}
      onUrlSubmit={e => { handleUrlIngest(e, chatUrlInput); setChatUrlInput(''); setShowChatUrl(false) }}
      urlLoading={urlLoading}
      provider={provider}
      onProviderChange={setProvider}
      cloudModel={cloudModel}
      onCloudModelChange={setCloudModel}
      cloudModels={CLOUD_MODELS}
      files={sessionFiles}
      onPreviewFile={name => setPreviewFile(name)}
      onRemoveFile={handleRemoveFile}
      footer={tokenStats && tokenStats.total > 0 ? (() => {
        const model = COST_MODELS.find(m => m.name === selectedCostModel) || COST_MODELS[0]
        const cost  = (tokenStats.prompt / 1e6) * model.input + (tokenStats.completion / 1e6) * model.output
        return (
          <div className="flex items-center justify-center gap-1.5 mt-2 text-[10px]" style={{ color: 'var(--text-faint)' }}>
            <span>Est. cost on</span>
            <select
              aria-label="Cost reference model"
              className="text-[10px] cursor-pointer outline-none rounded-md px-1 py-0.5"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-soft)', color: 'var(--text-lo)' }}
              value={selectedCostModel}
              onChange={e => setSelectedCostModel(e.target.value)}
            >
              {COST_MODELS.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
            </select>
            <span className="font-medium" style={{ color: 'var(--text-lo)' }}>{cost < 0.0001 ? '<$0.0001' : `$${cost.toFixed(4)}`}</span>
            <span>· {tokenStats.total.toLocaleString()} tokens</span>
          </div>
        )
      })() : null}
    />
  )

  // ── Groq donut renderer ────────────────────────────────────────────────────
  const renderDonut = (model, label, limit) => {
    const data = groqTokens?.models?.[model]
    const used = data?.total ?? 0
    const dailyLimit = data?.daily_limit ?? limit
    const rawPct = Math.round(used / Math.max(dailyLimit, 1) * 100)
    const pct    = Math.min(rawPct, 100)
    const over   = rawPct > 100
    const tpmPct = (data?.tpm_limit != null && data?.tpm_remaining != null)
      ? Math.min(100, Math.round((1 - data.tpm_remaining / data.tpm_limit) * 100)) : null
    const tpmLow  = tpmPct != null && tpmPct >= 80
    const fillColor = (over || tpmLow || pct >= 90) ? 'var(--danger)' : pct >= 60 ? 'var(--warning)' : 'var(--success)'
    const r = 13; const circ = 2 * Math.PI * r
    return (
      <div key={model} className="flex items-center gap-2.5" title={`${model}\n${used.toLocaleString()} / ${dailyLimit.toLocaleString()} tpd`}>
        <div className="relative flex-shrink-0 w-8 h-8 flex items-center justify-center">
          <svg width="32" height="32" className="absolute inset-0">
            <circle cx="16" cy="16" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="2.5" />
            <circle cx="16" cy="16" r={r} fill="none" stroke={fillColor} strokeWidth="2.5"
              strokeDasharray={circ} strokeDashoffset={circ * (1 - pct / 100)}
              strokeLinecap="round" transform="rotate(-90 16 16)"
              style={{ transition: 'stroke-dashoffset 0.5s ease' }} />
          </svg>
          <span className="text-[8px] font-bold relative z-10" style={{ color: fillColor }}>
            {over ? `${rawPct}%` : `${pct}%`}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[10px] font-medium" style={{ color: 'var(--text-hi)' }}>{label}</div>
          <div className="text-[9px] truncate" style={{ color: over ? 'var(--danger)' : 'var(--text-faint)' }}>
            {used.toLocaleString()} / {dailyLimit.toLocaleString()} tpd
            {over ? ' — limit exceeded' : tpmLow ? ' ⚠' : ''}
          </div>
        </div>
      </div>
    )
  }

  // ─────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <TooltipProvider delayDuration={300}>
      <div
        className="flex flex-col h-screen overflow-hidden relative"
        style={{ background: 'var(--bg-base)' }}
        onDragOver={ev => { ev.preventDefault(); setIsDragOver(true) }}
        onDragEnter={ev => { ev.preventDefault(); setIsDragOver(true) }}
        onDragLeave={ev => { if (!ev.currentTarget.contains(ev.relatedTarget)) setIsDragOver(false) }}
        onDrop={ev => { ev.preventDefault(); setIsDragOver(false); handleFileSelect(ev.dataTransfer.files) }}
      >
        {/* Always-mounted file input */}
        <input
          ref={fileInputRef} type="file"
          accept=".pdf,.txt,.docx,.xlsx,.xls,.pptx,.puml,.plantuml,.uml,.md,.csv,image/*"
          multiple style={{ display: 'none' }}
          onChange={ev => { handleFileSelect(ev.target.files); ev.target.value = '' }}
        />

        {/* Drag overlay */}
        <AnimatePresence>
          {isDragOver && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-50 flex items-center justify-center pointer-events-none"
              style={{ background: 'rgba(9,9,11,0.82)', backdropFilter: 'blur(8px)' }}
            >
              <motion.div
                initial={{ scale: 0.92, y: 8 }}
                animate={{ scale: 1, y: 0 }}
                className="dashed-anim rounded-3xl p-14 flex flex-col items-center gap-4"
                style={{ background: 'color-mix(in srgb, var(--primary) 6%, transparent)' }}
              >
                <motion.div
                  animate={{ y: [0, -8, 0] }}
                  transition={{ repeat: Infinity, duration: 1.6, ease: 'easeInOut' }}
                >
                  <Upload className="w-12 h-12" style={{ color: 'var(--accent-1)' }} />
                </motion.div>
                <div className="text-center">
                  <p className="text-sm font-semibold" style={{ color: 'var(--text-hi)' }}>Drop files to upload</p>
                  <p className="text-xs mt-1" style={{ color: 'var(--text-lo)' }}>PDF, Word, PowerPoint, Excel, images, markdown…</p>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Body ── */}
        <div className="flex flex-1 overflow-hidden relative z-10">

          {/* ── Left panel ── */}
          <motion.aside
            initial={false}
            animate={{ width: showLeftSidebar ? 276 : 0 }}
            transition={SPRING}
            className="flex-shrink-0 overflow-hidden relative"
            aria-label="Chat sessions"
            aria-hidden={!showLeftSidebar}
          >
            <motion.div
              animate={{ opacity: showLeftSidebar ? 1 : 0, x: showLeftSidebar ? 0 : -16 }}
              transition={{ duration: 0.22 }}
              className="glass-subtle w-[276px] h-full flex flex-col border-y-0 border-l-0"
              style={{ background: 'var(--bg-secondary)' }}
            >
              {/* Header */}
              <div className="flex items-center gap-2.5 px-4 h-14 flex-shrink-0" style={{ borderBottom: '1px solid var(--border-soft)' }}>
                <LogoMark />
                <span className="font-semibold text-sm tracking-tight flex-1" style={{ color: 'var(--text-hi)' }}>
                  RAG Assistant
                </span>
                <GhostIconButton title="Close sidebar (Ctrl+B)" onClick={() => setShowLeftSidebar(false)}>
                  <PanelLeftClose className="w-4 h-4" />
                </GhostIconButton>
              </div>

              {/* New chat + search */}
              <div className="p-3 space-y-2 flex-shrink-0">
                <motion.button
                  type="button"
                  whileHover={{ scale: 1.015 }}
                  whileTap={{ scale: 0.985 }}
                  onClick={createSession}
                  className="w-full h-9 rounded-sm flex items-center justify-center gap-2 text-xs font-medium text-white"
                  style={{ background: 'var(--primary)' }}
                >
                  <Plus className="h-3.5 w-3.5" /> New chat
                  <kbd className="ml-1 text-[8px] px-1 py-px rounded bg-white/15 font-sans">⌘⇧O</kbd>
                </motion.button>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 pointer-events-none" style={{ color: 'var(--text-faint)' }} />
                  <input
                    ref={searchInputRef}
                    className="w-full h-9 rounded-md pl-9 pr-8 text-xs outline-none transition-all placeholder:text-[var(--text-faint)] focus:ring-1 focus:ring-[var(--primary)]"
                    style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-soft)', color: 'var(--text-hi)' }}
                    placeholder="Search chats…  (Ctrl+K)"
                    aria-label="Search chats"
                    value={sessionSearch}
                    onChange={e => setSessionSearch(e.target.value)}
                  />
                  {sessionSearch && (
                    <button className="absolute right-2.5 top-1/2 -translate-y-1/2" aria-label="Clear search" onClick={() => setSessionSearch('')}>
                      <X className="h-3 w-3" style={{ color: 'var(--text-faint)' }} />
                    </button>
                  )}
                </div>
              </div>

              {/* Session list */}
              <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5" role="list">
                {visibleSessions.length === 0 ? (
                  <p className="text-xs text-center py-6" style={{ color: 'var(--text-faint)' }}>
                    No chats match "{sessionSearch}"
                  </p>
                ) : (
                  <AnimatePresence mode="popLayout" initial={false}>
                    {visibleSessions.map(s => (
                      <SessionItem
                        key={s.id}
                        session={s}
                        active={s.id === activeSession?.id}
                        excerpt={excerptFor(s)}
                        onSelect={() => switchSession(s.id)}
                        onDelete={() => { if (window.confirm('Delete this chat?')) deleteSession(s.id) }}
                      />
                    ))}
                  </AnimatePresence>
                )}
              </div>

              {/* Groq usage (when cloud) */}
              <AnimatePresence>
                {provider === 'cloud' && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="flex-shrink-0 overflow-hidden"
                    style={{ borderTop: '1px solid var(--border-soft)' }}
                  >
                    <div className="px-4 py-3 flex items-center gap-2">
                      <div className="flex-1 min-w-0">
                        {(() => {
                          const m = CLOUD_MODELS.find(m => m.key === cloudModel) || CLOUD_MODELS[0]
                          return renderDonut(m.key, m.label, m.limit)
                        })()}
                      </div>
                      <GhostIconButton
                        title={showAllModels ? 'Hide all models' : 'Show all models'}
                        onClick={() => setShowAllModels(p => !p)}
                      >
                        <BarChart2 className="w-3.5 h-3.5" />
                      </GhostIconButton>
                    </div>
                    <AnimatePresence>
                      {showAllModels && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="px-4 pb-3 space-y-2.5 overflow-hidden"
                        >
                          {CLOUD_MODELS.map(({ key, label, limit }) => (
                            <div key={key} className={cn('transition-opacity', key === cloudModel ? 'opacity-100' : 'opacity-50')}>
                              {renderDonut(key, label, limit)}
                            </div>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* User footer */}
              <div
                className="flex items-center gap-2.5 px-3.5 py-3 flex-shrink-0"
                style={{ borderTop: '1px solid var(--border-soft)' }}
              >
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-semibold text-white flex-shrink-0 select-none"
                  style={{ background: 'var(--primary)' }}
                  aria-hidden="true"
                >
                  {currentUser.firstname?.[0]}{currentUser.lastname?.[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium truncate" style={{ color: 'var(--text-hi)' }}>
                    {currentUser.firstname} {currentUser.lastname}
                  </div>
                  <div className="text-[10px] truncate" style={{ color: 'var(--text-faint)' }}>{currentUser.email}</div>
                </div>
                {anyIndexing && <Loader2 className="w-3 h-3 animate-spin flex-shrink-0" style={{ color: 'var(--warning)' }} />}
                <GhostIconButton title="Usage & stats" onClick={openDashboard}>
                  <BarChart2 className="h-3.5 w-3.5" />
                </GhostIconButton>
                {history.filter(e => e.answer !== null).length > 0 && (
                  <GhostIconButton title="Export chat (PDF)" onClick={() => window.print()}>
                    <Printer className="h-3.5 w-3.5" />
                  </GhostIconButton>
                )}
                <GhostIconButton title="Sign out" onClick={onLogout}>
                  <LogOut className="h-3.5 w-3.5" />
                </GhostIconButton>
              </div>
            </motion.div>
          </motion.aside>

          {/* ── Chat area ── */}
          <main className="flex-1 flex flex-col overflow-hidden min-w-0 relative">

            {/* Top bar */}
            <div
              className="glass-subtle h-12 flex items-center px-2.5 gap-1.5 flex-shrink-0 border-x-0 border-t-0 no-print"
              style={{ background: 'var(--bg-base)' }}
            >
              {!showLeftSidebar && (
                <GhostIconButton title="Open sidebar (Ctrl+B)" onClick={() => setShowLeftSidebar(true)}>
                  <PanelLeft className="h-4 w-4" />
                </GhostIconButton>
              )}
              <div className="flex-1 flex items-center justify-center gap-2 min-w-0 px-2">
                <span className="text-xs font-medium truncate" style={{ color: 'var(--text-lo)' }}>
                  {activeSession?.name || 'New chat'}
                </span>
                <span
                  className="hidden sm:inline-flex items-center gap-1 text-[9px] font-medium rounded-full px-2 py-0.5 flex-shrink-0"
                  style={{
                    color: provider === 'cloud' ? 'var(--accent-2)' : 'var(--accent-1)',
                    background: provider === 'cloud' ? 'var(--accent-2-dim)' : 'var(--accent-1-dim)',
                  }}
                >
                  {provider === 'cloud' ? <Cloud className="w-2.5 h-2.5" /> : <Cpu className="w-2.5 h-2.5" />}
                  {provider === 'cloud' ? (CLOUD_MODELS.find(m => m.key === cloudModel)?.label || 'Groq') : 'Local'}
                </span>
                {anyIndexing && (
                  <span className="flex items-center gap-1 text-[10px] flex-shrink-0" style={{ color: 'var(--warning)' }}>
                    <Loader2 className="w-2.5 h-2.5 animate-spin" />
                    <span className="hidden sm:inline">Indexing…</span>
                  </span>
                )}
              </div>
              {!showRightSidebar ? (
                <GhostIconButton title="Open files panel (Ctrl+Shift+B)" onClick={() => setShowRightSidebar(true)}>
                  <PanelRight className="h-4 w-4" />
                </GhostIconButton>
              ) : (
                <div className="w-8" />
              )}
            </div>

            {/* Print header */}
            <div className="print-header hidden print:block px-6 py-4">
              <div className="font-semibold">RAG Assistant — Chat Export</div>
              <div className="text-sm">{new Date().toLocaleString()}</div>
            </div>

            {history.length === 0 && !isLoading ? (
              /* ── Empty state ── */
              <div className="flex-1 flex items-center justify-center px-6 pb-16 relative overflow-hidden">
                <Spotlight className="-top-20 left-1/2 -translate-x-1/2" fill="white" />
                <motion.div
                  initial="hidden"
                  animate="show"
                  variants={{ hidden: {}, show: { transition: { staggerChildren: 0.08 } } }}
                  className="w-full max-w-2xl space-y-6 relative z-10"
                >
                  <motion.div
                    variants={{ hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: SPRING } }}
                    className="text-center select-none"
                  >
                    <TextGenerateEffect
                      words={`How can I help you today${currentUser.firstname ? `, ${currentUser.firstname}` : ''}?`}
                      className="text-2xl font-semibold tracking-tight"
                      duration={0.3}
                    />
                    <p className="text-sm mt-2" style={{ color: 'var(--text-lo)' }}>
                      Upload documents and ask anything — answers come with citations.
                    </p>
                  </motion.div>

                  {/* Suggestion cards */}
                  <motion.div variants={{ hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: SPRING } }}>
                    <HoverEffect
                      className="w-full"
                      items={[
                        { title: 'Summarize my documents', description: 'Get a quick overview of all uploaded files', onClick: () => setQuestion('Summarize the uploaded documents') },
                        { title: 'Key concepts & terms', description: 'Extract the main ideas and definitions', onClick: () => setQuestion('What are the key concepts and terms in these documents?') },
                        { title: 'Compare & contrast', description: 'Find similarities and differences across files', onClick: () => setQuestion('Compare and contrast the main topics across the uploaded documents') },
                      ]}
                    />
                  </motion.div>

                  <motion.div variants={{ hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: SPRING } }}>
                    {composerEl}
                  </motion.div>
                </motion.div>
              </div>
            ) : (
              /* ── Active conversation ── */
              <>
                <div className="flex-1 overflow-y-auto px-4 py-6" ref={chatScrollRef}>
                  <div className="max-w-3xl mx-auto space-y-7">
                    {history.map(entry => (
                      <motion.div
                        key={entry.id}
                        id={`msg-${entry.id}`}
                        initial={{ opacity: 0, y: 14 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={SPRING}
                        className="space-y-3.5"
                      >
                        {/* User bubble */}
                        <div className="flex justify-end">
                          <div className="max-w-[75%] group">
                            <div
                              className="rounded-2xl rounded-tr-md px-4 py-2.5 text-sm leading-relaxed text-white"
                              style={{ background: 'var(--primary)' }}
                            >
                              {entry.question}
                            </div>
                            <div className="flex justify-end items-center gap-2 mt-1.5 px-1">
                              {entry.sentAt && (
                                <span className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
                                  {new Date(entry.sentAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                              )}
                              <span className="opacity-0 group-hover:opacity-100 transition-opacity">
                                <CopyButton text={entry.question} />
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Assistant response */}
                        <div className="flex justify-start">
                          <div className="max-w-[88%] w-full flex items-start gap-3">
                            {/* Avatar */}
                            <div
                              className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                              style={{ background: 'var(--accent-1-dim)', border: '1px solid color-mix(in srgb, var(--primary) 25%, transparent)' }}
                              aria-hidden="true"
                            >
                              <MessageSquare className="w-4 h-4" style={{ color: 'var(--primary)' }} />
                            </div>

                            <div className="flex-1 min-w-0 space-y-2">
                              {entry.answer === null ? (
                                <div className="glass rounded-2xl rounded-tl-md px-4 py-3.5 w-fit">
                                  <TypingIndicator label={entry.indexingWait ? 'Waiting for indexing…' : 'Thinking…'} />
                                </div>
                              ) : entry.rateLimitError ? (
                                <div
                                  className="rounded-2xl rounded-tl-md px-4 py-3 flex items-start gap-3"
                                  style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)' }}
                                  role="alert"
                                >
                                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: 'var(--danger)' }} />
                                  <div>
                                    <div className="font-medium text-sm" style={{ color: 'var(--danger)' }}>Rate limit reached</div>
                                    <div className="text-xs mt-0.5 leading-relaxed" style={{ color: 'rgba(239,68,68,0.8)' }}>
                                      {entry.rateLimitDaily
                                        ? "Groq's daily token quota is exhausted. Try again tomorrow or switch to a different model."
                                        : "Groq's per-minute limit was hit. Wait 1–2 minutes and try again, or reduce context by removing documents."}
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div className="group">
                                  <div className={cn('markdown-body', entry.id === streamingId && entry.answer && 'stream-caret')}>
                                    <Markdown>{entry.answer}</Markdown>
                                  </div>
                                  {entry.stopped && (
                                    <div className="flex items-center gap-1 text-xs mt-2" style={{ color: 'var(--text-faint)' }}>
                                      <Square className="w-3 h-3" /> Stopped
                                    </div>
                                  )}
                                  <div className="opacity-0 group-hover:opacity-100 transition-opacity mt-2.5 no-print">
                                    <CopyButton text={entry.answer} />
                                  </div>
                                </div>
                              )}

                              {/* Warning */}
                              {entry.warning && (
                                <div
                                  className="px-3.5 py-2.5 rounded-xl text-xs leading-relaxed flex items-start gap-2"
                                  style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)', color: 'var(--warning)' }}
                                >
                                  <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-px" />
                                  {entry.warning}
                                </div>
                              )}

                              {/* Citations */}
                              {entry.sources?.length > 0 && entry.answer !== null && (
                                <motion.div
                                  initial="hidden"
                                  animate="show"
                                  variants={{ hidden: {}, show: { transition: { staggerChildren: 0.05 } } }}
                                  className="flex flex-wrap gap-1.5 pt-0.5"
                                  aria-label="Citations"
                                >
                                  {(entry.citations?.length > 0 ? entry.citations : entry.sources.map(s => ({ file: s, pages: [] }))).map((c, i) => {
                                    const { Icon, color } = fileMeta(c.file)
                                    return (
                                      <motion.button
                                        key={i}
                                        type="button"
                                        variants={{ hidden: { opacity: 0, scale: 0.85, y: 4 }, show: { opacity: 1, scale: 1, y: 0 } }}
                                        whileHover={{ scale: 1.05, y: -1 }}
                                        onClick={() => globalFiles[c.file]?.status === 'ready' && setPreviewFile(c.file)}
                                        className="glass-subtle inline-flex items-center gap-1.5 rounded-full pl-2 pr-2.5 py-1 text-[10px] transition-colors cursor-pointer"
                                        style={{ color: 'var(--text-lo)' }}
                                        title={c.file}
                                      >
                                        <Icon className="w-2.5 h-2.5" style={{ color }} />
                                        <span className="max-w-[160px] truncate">{c.file}</span>
                                        {c.pages?.length > 0 && (
                                          <span style={{ color: 'var(--text-faint)' }}>p.{c.pages.join(',')}</span>
                                        )}
                                      </motion.button>
                                    )
                                  })}
                                </motion.div>
                              )}

                              {/* Eval badges + hypothesis */}
                              {(entry.eval || entry.hypothesis) && entry.answer !== null && (
                                <div className="space-y-1.5">
                                  <div className="flex gap-1.5 pt-0.5 items-center flex-wrap">
                                    {entry.eval && (
                                      <>
                                        {[['F', entry.eval.faithfulness, 'Faithfulness'], ['R', entry.eval.answer_relevance, 'Answer relevance']].map(([k, v, t]) => (
                                          <span
                                            key={k}
                                            className="text-[10px] px-1.5 py-0.5 rounded-md font-medium"
                                            style={{
                                              color: evalColor(v),
                                              background: `color-mix(in srgb, ${evalColor(v)} 12%, transparent)`,
                                              border: `1px solid color-mix(in srgb, ${evalColor(v)} 30%, transparent)`,
                                            }}
                                            title={t}
                                          >
                                            {k} {Math.round(v * 100)}%
                                          </span>
                                        ))}
                                      </>
                                    )}
                                    {entry.hypothesis && (
                                      <motion.button
                                        whileHover={{ scale: 1.1 }}
                                        whileTap={{ scale: 0.9 }}
                                        type="button"
                                        className="flex items-center justify-center w-5 h-5 rounded-md transition-colors"
                                        style={{
                                          color: hypothesisOpenId === entry.id ? 'var(--accent-1)' : 'var(--text-faint)',
                                          background: hypothesisOpenId === entry.id ? 'var(--accent-1-dim)' : 'rgba(255,255,255,0.04)',
                                          border: '1px solid var(--border-soft)',
                                        }}
                                        onClick={() => setHypothesisOpenId(hypothesisOpenId === entry.id ? null : entry.id)}
                                        title="Search hypothesis"
                                        aria-label="Toggle search hypothesis"
                                        aria-expanded={hypothesisOpenId === entry.id}
                                      >
                                        <Search className="w-2.5 h-2.5" />
                                      </motion.button>
                                    )}
                                  </div>
                                  <AnimatePresence>
                                    {hypothesisOpenId === entry.id && entry.hypothesis && (
                                      <motion.div
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        exit={{ opacity: 0, height: 0 }}
                                        className="overflow-hidden"
                                      >
                                        <div className="text-xs rounded-xl glass-subtle px-3.5 py-2.5 leading-relaxed" style={{ color: 'var(--text-lo)' }}>
                                          <span className="text-[10px] font-medium block mb-1" style={{ color: 'var(--accent-1)' }}>Search hypothesis</span>
                                          {entry.hypothesis}
                                        </div>
                                      </motion.div>
                                    )}
                                  </AnimatePresence>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                    <div ref={chatEndRef} />
                  </div>
                </div>

                {/* Scroll to bottom */}
                <AnimatePresence>
                  {showScrollDown && (
                    <motion.button
                      initial={{ opacity: 0, y: 8, scale: 0.9 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 8, scale: 0.9 }}
                      whileHover={{ scale: 1.08 }}
                      whileTap={{ scale: 0.92 }}
                      className="glass absolute bottom-40 left-1/2 -translate-x-1/2 rounded-full p-2.5 z-10 no-print"
                      onClick={scrollToBottom}
                      aria-label="Scroll to latest message"
                    >
                      <ChevronDown className="w-4 h-4" style={{ color: 'var(--text-lo)' }} />
                    </motion.button>
                  )}
                </AnimatePresence>

                {/* Floating composer */}
                <div className="flex-shrink-0 px-4 pb-4 pt-1 relative z-10 no-print">
                  <div className="max-w-3xl mx-auto">
                    {composerEl}
                  </div>
                </div>
              </>
            )}
          </main>

          {/* ── Right panel ── */}
          <motion.aside
            initial={false}
            animate={{ width: showRightSidebar ? 304 : 0 }}
            transition={SPRING}
            className="flex-shrink-0 overflow-hidden relative"
            aria-label="Documents"
            aria-hidden={!showRightSidebar}
          >
            <motion.div
              animate={{ opacity: showRightSidebar ? 1 : 0, x: showRightSidebar ? 0 : 16 }}
              transition={{ duration: 0.22 }}
              className="w-[304px] h-full flex flex-col"
              style={{ background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border-soft)' }}
            >
              {/* Header with tabs + close */}
              <div className="flex items-center h-14 px-2 flex-shrink-0 gap-1" style={{ borderBottom: '1px solid var(--border-soft)' }}>
                <div className="flex flex-1" role="tablist" aria-label="Panel tabs">
                  {['files', 'usage'].map(tab => (
                    <button
                      key={tab}
                      role="tab"
                      aria-selected={rightSidebarTab === tab}
                      className="relative flex-1 py-2 text-xs font-medium capitalize transition-colors"
                      style={{ color: rightSidebarTab === tab ? 'var(--text-hi)' : 'var(--text-faint)' }}
                      onClick={() => setRightSidebarTab(tab)}
                    >
                      {tab}
                      {rightSidebarTab === tab && (
                        <motion.span
                          layoutId="right-tab-underline"
                          className="absolute bottom-0 left-1/4 right-1/4 h-0.5 rounded-full"
                          style={{ background: 'var(--primary)' }}
                          transition={{ type: 'spring', stiffness: 500, damping: 36 }}
                        />
                      )}
                    </button>
                  ))}
                </div>
                <GhostIconButton title="Close panel (Ctrl+Shift+B)" onClick={() => setShowRightSidebar(false)}>
                  <PanelRightClose className="w-4 h-4" />
                </GhostIconButton>
              </div>

              {rightSidebarTab === 'usage' ? (
                /* ── Usage tab ── */
                <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
                  <div
                    className="flex items-center rounded-lg p-0.5 gap-0.5 w-fit"
                    style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-soft)' }}
                    role="radiogroup"
                  >
                    {['daily', 'monthly'].map(p => (
                      <button
                        key={p}
                        role="radio"
                        aria-checked={usagePeriod === p}
                        onClick={() => setUsagePeriod(p)}
                        className="relative px-3 py-1 rounded-md text-[10px] font-medium capitalize transition-colors"
                        style={{ color: usagePeriod === p ? 'var(--text-hi)' : 'var(--text-faint)' }}
                      >
                        {usagePeriod === p && (
                          <motion.span
                            layoutId="usage-period-pill"
                            className="absolute inset-0 rounded-md"
                            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-med)' }}
                            transition={{ type: 'spring', stiffness: 500, damping: 36 }}
                          />
                        )}
                        <span className="relative z-10">{p}</span>
                      </button>
                    ))}
                  </div>
                  {(() => {
                    const key = `rag-usage-${currentUser?.email || 'default'}`
                    let raw = {}
                    try { raw = JSON.parse(localStorage.getItem(key) || '{}') } catch {}
                    let chartData = []
                    if (usagePeriod === 'daily') {
                      chartData = Object.entries(raw).sort(([a],[b]) => a.localeCompare(b)).slice(-14)
                        .map(([date, d]) => ({ label: date.slice(5), tokens: d.total || 0, prompt: d.prompt || 0, completion: d.completion || 0 }))
                    } else {
                      const byMonth = {}
                      Object.entries(raw).forEach(([date, d]) => {
                        const m = date.slice(0, 7)
                        byMonth[m] = Math.max(byMonth[m] || 0, d.total || 0)
                      })
                      chartData = Object.entries(byMonth).sort(([a],[b]) => a.localeCompare(b)).slice(-6)
                        .map(([month, tokens]) => ({ label: month.slice(5), tokens }))
                    }
                    if (chartData.length === 0) return (
                      <div className="text-xs text-center py-10 leading-relaxed" style={{ color: 'var(--text-faint)' }}>
                        No usage data yet.<br />Start chatting to see your stats.
                      </div>
                    )
                    const total = chartData.reduce((a, d) => a + d.tokens, 0)
                    const last = chartData[chartData.length - 1]
                    return (
                      <div className="space-y-3">
                        <div className="glass rounded-xl px-4 py-3.5">
                          <div className="text-xl font-bold tracking-tight" style={{ color: 'var(--text-hi)' }}>{total.toLocaleString()}</div>
                          <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-faint)' }}>
                            {usagePeriod === 'daily' ? 'Tokens — last 14 days' : 'Peak tokens — last 6 months'}
                          </div>
                        </div>
                        <div className="h-40">
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                              <defs>
                                <linearGradient id="usageGrad" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor="#C026D3" stopOpacity={0.3} />
                                  <stop offset="95%" stopColor="#C026D3" stopOpacity={0} />
                                </linearGradient>
                              </defs>
                              <XAxis dataKey="label" tick={{ fontSize: 9, fill: '#64646E' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                              <RechartTooltip
                                contentStyle={{ backgroundColor: '#141417', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '10px', fontSize: '10px', padding: '6px 10px', color: '#FAFAFA' }}
                                labelStyle={{ color: '#A1A1AA', marginBottom: '2px' }}
                                formatter={(v) => [v.toLocaleString() + ' tokens', 'Usage']}
                              />
                              <Area type="monotone" dataKey="tokens" stroke="#C026D3" strokeWidth={1.5} fill="url(#usageGrad)" dot={false} />
                            </AreaChart>
                          </ResponsiveContainer>
                        </div>
                        {usagePeriod === 'daily' && last && (
                          <div className="grid grid-cols-2 gap-2">
                            {[
                              { label: 'Prompt (today)', value: last.prompt },
                              { label: 'Completion (today)', value: last.completion },
                            ].map(({ label, value }) => (
                              <div key={label} className="glass rounded-xl px-3 py-2.5 text-center">
                                <div className="text-sm font-bold" style={{ color: 'var(--text-hi)' }}>{(value || 0).toLocaleString()}</div>
                                <div className="text-[9px] mt-0.5" style={{ color: 'var(--text-faint)' }}>{label}</div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )
                  })()}
                </div>
              ) : (
                /* ── Files tab ── */
                <>
                  {/* Prompt navigator */}
                  {history.filter(e => e.question).length > 0 && (
                    <div className="flex-shrink-0" style={{ borderBottom: '1px solid var(--border-soft)' }}>
                      <button
                        type="button"
                        className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-medium transition-colors hover:bg-white/[0.03]"
                        onClick={() => setShowPromptNav(p => !p)}
                        aria-expanded={showPromptNav}
                      >
                        <span className="flex items-center gap-1.5" style={{ color: 'var(--text-lo)' }}>
                          <BookOpen className="w-3.5 h-3.5" style={{ color: 'var(--accent-2)' }} /> Prompt navigator
                        </span>
                        {showPromptNav
                          ? <ChevronUp className="w-3.5 h-3.5" style={{ color: 'var(--text-faint)' }} />
                          : <ChevronDown className="w-3.5 h-3.5" style={{ color: 'var(--text-faint)' }} />}
                      </button>
                      <AnimatePresence>
                        {showPromptNav && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="max-h-44 overflow-y-auto pb-1">
                              {history.filter(e => e.question).map((entry, idx) => (
                                <button
                                  key={entry.id}
                                  type="button"
                                  className="w-full text-left px-4 py-2 text-[10px] transition-colors flex gap-2 items-start hover:bg-white/[0.04] group"
                                  style={{ color: 'var(--text-lo)' }}
                                  onClick={() => document.getElementById(`msg-${entry.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                                >
                                  <span
                                    className="flex-shrink-0 w-4 h-4 rounded text-[9px] flex items-center justify-center font-medium transition-colors group-hover:text-[var(--accent-1)]"
                                    style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-faint)' }}
                                  >
                                    {idx + 1}
                                  </span>
                                  <span className="truncate group-hover:text-[var(--text-hi)] transition-colors">
                                    {entry.question.length > 50 ? entry.question.slice(0, 50) + '…' : entry.question}
                                  </span>
                                </button>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  )}

                  {/* Upload area + URL */}
                  <div className="px-3.5 pt-3.5 pb-2 flex-shrink-0 space-y-2">
                    <motion.button
                      type="button"
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      onClick={() => fileInputRef.current?.click()}
                      className={cn(
                        'w-full rounded-xl py-4 flex flex-col items-center gap-1.5 transition-all group',
                        isDragOver ? 'dashed-anim' : ''
                      )}
                      style={{
                        background: isDragOver ? 'color-mix(in srgb, var(--primary) 7%, transparent)' : 'rgba(255,255,255,0.02)',
                        border: isDragOver ? 'none' : '1.5px dashed var(--border-med)',
                      }}
                      aria-label="Upload documents"
                    >
                      <Upload
                        className="w-4 h-4 transition-transform group-hover:-translate-y-0.5"
                        style={{ color: 'var(--accent-1)' }}
                      />
                      <span className="text-[11px] font-medium" style={{ color: 'var(--text-lo)' }}>
                        Drop files or <span style={{ color: 'var(--accent-1)' }}>browse</span>
                      </span>
                      <span className="text-[9px]" style={{ color: 'var(--text-faint)' }}>
                        PDF · Word · PowerPoint · Excel · images
                      </span>
                    </motion.button>

                    <form className="flex gap-1.5" onSubmit={handleUrlIngest}>
                      <div className="relative flex-1">
                        <Link2 className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 pointer-events-none" style={{ color: 'var(--accent-2)' }} />
                        <input
                          className="w-full h-8 rounded-md pl-7 pr-2 text-xs outline-none transition-all placeholder:text-[var(--text-faint)] focus:ring-1 focus:ring-[var(--primary)]"
                          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-soft)', color: 'var(--text-hi)' }}
                          type="url"
                          placeholder="Paste a URL…"
                          aria-label="Ingest URL"
                          value={urlInput}
                          onChange={e => { setUrlInput(e.target.value); setUrlError('') }}
                          disabled={urlLoading}
                        />
                      </div>
                      <motion.button
                        type="submit"
                        whileHover={{ scale: 1.06 }}
                        whileTap={{ scale: 0.94 }}
                        className="h-8 w-8 rounded-sm flex items-center justify-center flex-shrink-0 disabled:opacity-40"
                        style={{ background: 'var(--accent-1-dim)', color: 'var(--accent-1)', border: '1px solid color-mix(in srgb, var(--primary) 25%, transparent)' }}
                        disabled={urlLoading || !urlInput.trim()}
                        aria-label="Ingest URL"
                      >
                        {urlLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
                      </motion.button>
                    </form>
                    {urlError && <p className="text-[10px]" style={{ color: 'var(--danger)' }} role="alert">{urlError}</p>}
                  </div>

                  {/* File list */}
                  <div className="flex-1 overflow-y-auto px-3.5 pb-4">
                    {/* Library */}
                    {(() => {
                      const libraryFiles = Object.keys(globalFiles).filter(name => !sessionFileNames.includes(name) && globalFiles[name]?.status === 'ready')
                      if (libraryFiles.length === 0) return null
                      return (
                        <div className="mb-3">
                          <p className="text-[9px] uppercase tracking-widest px-1 mb-1.5 mt-1 font-semibold" style={{ color: 'var(--text-faint)' }}>
                            Library
                          </p>
                          <div className="space-y-1">
                            {libraryFiles.map(name => {
                              const { Icon, color } = fileMeta(name)
                              return (
                                <motion.div
                                  key={name}
                                  layout
                                  initial={{ opacity: 0 }}
                                  animate={{ opacity: 1 }}
                                  className="group flex items-center gap-2 rounded-xl px-3 py-2 transition-all hover:bg-white/[0.03]"
                                  style={{ border: '1px dashed var(--border-med)' }}
                                >
                                  <Icon className="w-3.5 h-3.5 flex-shrink-0" style={{ color }} />
                                  <span className="text-xs truncate flex-1" style={{ color: 'var(--text-lo)' }} title={name}>{name}</span>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <motion.button
                                        whileHover={{ scale: 1.15 }}
                                        whileTap={{ scale: 0.85 }}
                                        className="p-1 rounded-md transition-colors hover:bg-white/[0.08] flex-shrink-0"
                                        style={{ color: 'var(--accent-1)' }}
                                        onClick={() => addFileToSession(name)}
                                        aria-label={`Add ${name} to session`}
                                      >
                                        <Plus className="w-3 h-3" />
                                      </motion.button>
                                    </TooltipTrigger>
                                    <TooltipContent>Add to session</TooltipContent>
                                  </Tooltip>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <motion.button
                                        whileHover={{ scale: 1.15 }}
                                        whileTap={{ scale: 0.85 }}
                                        className="p-1 rounded-md transition-colors hover:bg-white/[0.08] flex-shrink-0 opacity-0 group-hover:opacity-100"
                                        style={{ color: 'var(--text-faint)' }}
                                        onMouseEnter={e => (e.currentTarget.style.color = 'var(--danger)')}
                                        onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-faint)')}
                                        onClick={() => handleRemoveFile(name)}
                                        aria-label={`Delete ${name} from library`}
                                      >
                                        <X className="w-3 h-3" />
                                      </motion.button>
                                    </TooltipTrigger>
                                    <TooltipContent>Delete from library</TooltipContent>
                                  </Tooltip>
                                </motion.div>
                              )
                            })}
                          </div>
                        </div>
                      )
                    })()}

                    {sessionFiles.length > 0 && (
                      <>
                        <p className="text-[9px] uppercase tracking-widest px-1 mb-1.5 mt-1 font-semibold" style={{ color: 'var(--text-faint)' }}>
                          In this chat — {sessionFiles.length}
                        </p>
                        <div className="space-y-1.5">
                          <AnimatePresence mode="popLayout" initial={false}>
                            {sessionFiles.map(file => (
                              <FileCard
                                key={file.name}
                                file={file}
                                onPreview={setPreviewFile}
                                onRemove={handleRemoveFile}
                                onReindex={handleReindexFile}
                                onCancelIndexing={handleCancelIndexing}
                              />
                            ))}
                          </AnimatePresence>
                        </div>
                      </>
                    )}

                    {sessionFiles.length === 0 && Object.keys(globalFiles).length === 0 && (
                      <div className="text-center py-8 px-3">
                        <FileText className="w-6 h-6 mx-auto mb-2" style={{ color: 'var(--text-faint)' }} />
                        <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-faint)' }}>
                          No documents yet. Upload files or paste a URL to start asking questions.
                        </p>
                      </div>
                    )}
                  </div>
                </>
              )}
            </motion.div>
          </motion.aside>
        </div>

        {/* ── Dashboard Sheet ── */}
        <Sheet open={showDashboard} onOpenChange={setShowDashboard}>
          <SheetContent className="w-[520px] sm:max-w-none overflow-y-auto p-0 glass-strong border-l" side="right">
            <SheetHeader className="px-6 py-4 sticky top-0 z-10 glass-strong border-x-0 border-t-0 rounded-none">
              <SheetTitle style={{ color: 'var(--text-hi)' }}>Usage & Statistics</SheetTitle>
            </SheetHeader>
            <div className="px-6 py-5 space-y-6">
              {!dashboardData ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    {[0, 1, 2, 3].map(i => <div key={i} className="skeleton h-20" />)}
                  </div>
                  <div className="skeleton h-32" />
                </div>
              ) : (
                <>
                  {/* Stats cards */}
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { label: 'Questions asked',   value: dashboardData.queries?.total ?? totalQuestions },
                      { label: 'Avg response time', value: dashboardData.queries?.avg_response_ms ? `${(dashboardData.queries.avg_response_ms / 1000).toFixed(1)}s` : '—' },
                      { label: 'Documents ready',   value: dashboardData.documents.ready },
                      { label: 'Total chunks',      value: dashboardData.chunks.total },
                    ].map(({ label, value }, i) => (
                      <motion.div
                        key={label}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ ...SPRING, delay: i * 0.05 }}
                        className="glass card-lift rounded-2xl p-4"
                      >
                        <div className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-hi)' }}>{value}</div>
                        <div className="text-xs mt-0.5" style={{ color: 'var(--text-faint)' }}>{label}</div>
                      </motion.div>
                    ))}
                  </div>

                  {/* RAG quality */}
                  {evalEntries.length > 0 && (
                    <div>
                      <h3 className="text-[10px] font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--text-faint)' }}>
                        RAG Quality — avg over {evalEntries.length} response{evalEntries.length !== 1 ? 's' : ''}
                      </h3>
                      <div className="grid grid-cols-2 gap-3">
                        {[
                          { label: 'Avg Faithfulness', value: avgFaithfulness, title: 'How well answers are grounded in retrieved context' },
                          { label: 'Avg Relevance',    value: avgRelevance,    title: 'How directly answers address the questions' },
                        ].map(({ label, value, title }) => (
                          <div key={label} className="glass rounded-2xl p-4" title={title}>
                            <div className="text-2xl font-bold" style={{ color: evalColor(value) }}>
                              {Math.round(value * 100)}%
                            </div>
                            <div className="text-xs mt-0.5" style={{ color: 'var(--text-faint)' }}>{label}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Active models */}
                  <div>
                    <h3 className="text-[10px] font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--text-faint)' }}>Active Models</h3>
                    <div className="rounded-2xl overflow-hidden divide-y divide-[var(--border-soft)]" style={{ border: '1px solid var(--border-soft)', background: 'var(--bg-card)' }}>
                      {[['LLM', provider === 'cloud' ? cloudModel : dashboardData.models.llm], ['Embeddings', dashboardData.models.embed], ['Vision', dashboardData.models.vision]].map(([label, value]) => (
                        <div key={label} className="flex items-center justify-between px-4 py-2.5">
                          <span className="text-xs" style={{ color: 'var(--text-lo)' }}>{label}</span>
                          <code className="text-[11px] px-2 py-0.5 rounded-md" style={{ background: 'var(--accent-1-dim)', color: 'var(--text-hi)' }}>{value}</code>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Token usage */}
                  <div>
                    <h3 className="text-[10px] font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--text-faint)' }}>Token Usage (session)</h3>
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { label: 'Prompt',     value: dashboardData.tokens.prompt.toLocaleString() },
                        { label: 'Completion', value: dashboardData.tokens.completion.toLocaleString() },
                        { label: 'Total',      value: dashboardData.tokens.total.toLocaleString() },
                      ].map(({ label, value }) => (
                        <div key={label} className="glass rounded-xl px-3 py-3 text-center">
                          <div className="text-lg font-bold" style={{ color: 'var(--text-hi)' }}>{value}</div>
                          <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-faint)' }}>{label}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Cost estimate */}
                  {dashboardData.tokens.total > 0 && (
                    <div>
                      <h3 className="text-[10px] font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--text-faint)' }}>Estimated Cost</h3>
                      <div className="rounded-2xl overflow-hidden divide-y divide-[var(--border-soft)]" style={{ border: '1px solid var(--border-soft)', background: 'var(--bg-card)' }}>
                        {COST_MODELS.map(({ name, input, output }) => {
                          const cost = (dashboardData.tokens.prompt / 1e6) * input + (dashboardData.tokens.completion / 1e6) * output
                          return (
                            <div key={name} className="flex items-center justify-between px-4 py-2">
                              <span className="text-xs" style={{ color: 'var(--text-lo)' }}>{name}</span>
                              <span className="text-xs font-medium" style={{ color: 'var(--text-hi)' }}>{cost < 0.001 ? '<$0.001' : `$${cost.toFixed(4)}`}</span>
                            </div>
                          )
                        })}
                      </div>
                      <p className="text-[10px] mt-2" style={{ color: 'var(--text-faint)' }}>Prices per 1M tokens. Resets on server restart.</p>
                    </div>
                  )}

                  {/* Documents */}
                  {Object.keys(dashboardData.documents.file_chunks).length > 0 && (
                    <div>
                      <h3 className="text-[10px] font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--text-faint)' }}>Documents</h3>
                      <div className="rounded-2xl overflow-hidden divide-y divide-[var(--border-soft)]" style={{ border: '1px solid var(--border-soft)', background: 'var(--bg-card)' }}>
                        {Object.entries(dashboardData.documents.file_chunks).map(([name, chunks]) => {
                          const cv = chunkView[name] || {}
                          const sv = summaryView[name] || {}

                          const toggleChunks = async () => {
                            if (cv.open) { setChunkView(p => ({ ...p, [name]: { ...p[name], open: false } })); return }
                            if (cv.chunks) { setChunkView(p => ({ ...p, [name]: { ...p[name], open: true } })); return }
                            setChunkView(p => ({ ...p, [name]: { open: true, loading: true, chunks: null } }))
                            try {
                              const res  = await authFetch(`${API}/debug/chunks/${encodeURIComponent(name)}`)
                              const data = await res.json()
                              setChunkView(p => ({ ...p, [name]: { open: true, loading: false, chunks: data.chunks || [] } }))
                            } catch { setChunkView(p => ({ ...p, [name]: { open: true, loading: false, chunks: [] } })) }
                          }

                          const summarize = async (e) => {
                            e.stopPropagation()
                            if (sv.loading) return
                            if (sv.text) { setSummaryView(p => ({ ...p, [name]: { ...p[name], text: null } })); return }
                            setSummaryView(p => ({ ...p, [name]: { loading: true, text: null } }))
                            try {
                              let accumulated = ''
                              const res = await authFetch(`${API}/ask`, {
                                method: 'POST', headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ question: 'Résume ce document complètement : couvre tous les sujets principaux, points clés et détails importants. Ne saute rien.', files: [name], history: [] }),
                              })
                              const reader = res.body.getReader(); const decoder = new TextDecoder(); let buf = ''
                              while (true) {
                                const { done, value } = await reader.read(); if (done) break
                                buf += decoder.decode(value, { stream: true })
                                const lines = buf.split('\n'); buf = lines.pop()
                                for (const line of lines) {
                                  if (!line.startsWith('data: ')) continue
                                  try { const msg = JSON.parse(line.slice(6)); if (msg.type === 'token') accumulated += msg.content } catch {}
                                }
                                setSummaryView(p => ({ ...p, [name]: { loading: false, text: accumulated || '…' } }))
                              }
                            } catch { setSummaryView(p => ({ ...p, [name]: { loading: false, text: 'Error generating summary.' } })) }
                          }

                          return (
                            <div key={name}>
                              <div className="px-4 py-2.5 cursor-pointer transition-colors hover:bg-white/[0.03]" onClick={toggleChunks}>
                                <div className="flex items-center justify-between gap-2">
                                  <div className="flex items-center gap-2 min-w-0">
                                    <ChevronDown className={cn('w-3 h-3 flex-shrink-0 transition-transform', cv.open ? '' : '-rotate-90')} style={{ color: 'var(--text-faint)' }} />
                                    <span className="text-xs truncate" style={{ color: 'var(--text-hi)' }}>{name}</span>
                                  </div>
                                  <div className="flex items-center gap-2 flex-shrink-0">
                                    <button
                                      onClick={summarize}
                                      className="text-[10px] px-2 py-0.5 rounded-md transition-colors"
                                      style={sv.text
                                        ? { background: 'var(--accent-1)', color: '#fff', border: '1px solid var(--accent-1)' }
                                        : { color: 'var(--text-lo)', border: '1px solid var(--border-med)', opacity: sv.loading ? 0.6 : 1 }}
                                      title="Generate a summary"
                                    >
                                      {sv.loading ? '…' : sv.text ? '✕ Summary' : '∑ Summarize'}
                                    </button>
                                    <span className="text-[10px]" style={{ color: 'var(--text-faint)' }}>{chunks} chunks</span>
                                  </div>
                                </div>
                              </div>

                              {sv.text && (
                                <div className="mx-4 mb-3 p-3 rounded-xl text-xs leading-relaxed whitespace-pre-wrap" style={{ background: 'color-mix(in srgb, var(--primary) 6%, transparent)', borderLeft: '2px solid var(--accent-1)', color: 'var(--text-hi)' }}>
                                  <span className="text-[10px] font-medium block mb-1" style={{ color: 'var(--accent-1)' }}>Summary — {name}</span>
                                  {sv.text}
                                </div>
                              )}

                              {cv.open && (
                                <div className="mx-4 mb-3 space-y-2">
                                  {cv.loading && <div className="skeleton h-10" />}
                                  {cv.chunks && cv.chunks.length === 0 && <p className="text-xs" style={{ color: 'var(--text-faint)' }}>No chunks found.</p>}
                                  {cv.chunks && cv.chunks.map((text, i) => (
                                    <div key={i} className="p-2.5 rounded-xl text-xs leading-relaxed whitespace-pre-wrap" style={{ background: 'rgba(255,255,255,0.03)', borderLeft: '2px solid color-mix(in srgb, var(--primary) 40%, transparent)', color: 'var(--text-lo)' }}>
                                      <span className="text-[9px] font-medium block mb-1" style={{ color: 'var(--text-faint)' }}>Chunk {i + 1}</span>
                                      {text}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* Retrieval eval */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-faint)' }}>Retrieval Evaluation</h3>
                      <Button size="sm" variant="outline" className="h-7 text-xs rounded-lg" onClick={runEval} disabled={evalLoading}>
                        {evalLoading ? <><Loader2 className="w-3 h-3 mr-1.5 animate-spin" />Running…</> : 'Run eval'}
                      </Button>
                    </div>

                    {!evalData && !evalLoading && (
                      <p className="text-xs leading-relaxed" style={{ color: 'var(--text-faint)' }}>
                        Measures Hit Rate, Precision, MRR and Recall against <code className="text-[11px]">eval_dataset.json</code>.
                        Make sure dataset files are indexed before running.
                      </p>
                    )}
                    {evalLoading && (
                      <div className="space-y-2">
                        <div className="skeleton h-8" />
                        <div className="skeleton h-24" />
                        <p className="text-xs italic" style={{ color: 'var(--text-faint)' }}>Running retrieval for each question — this may take 30–60 s…</p>
                      </div>
                    )}
                    {evalData?.error && <p className="text-xs" style={{ color: 'var(--danger)' }}>{evalData.error}</p>}

                    {evalData && !evalData.error && (
                      <div className="space-y-3">
                        {evalData.configurations && (
                          <div className="rounded-2xl overflow-hidden" style={{ border: '1px solid var(--border-soft)' }}>
                            <div className="grid grid-cols-3 px-3 py-2 text-[10px] font-semibold uppercase" style={{ background: 'var(--bg-elevated)', color: 'var(--text-faint)' }}>
                              <span>Configuration</span>
                              <span className="text-right">Hit@{evalData.top_k}</span>
                              <span className="text-right">MRR</span>
                            </div>
                            {evalData.configurations.map(cfg => (
                              <div key={cfg.name} className="grid grid-cols-3 px-3 py-2 text-xs" style={{ borderTop: '1px solid var(--border-soft)', background: cfg.name === 'Hybrid + Reranker' ? 'color-mix(in srgb, var(--primary) 6%, transparent)' : 'transparent', fontWeight: cfg.name === 'Hybrid + Reranker' ? 500 : 400 }}>
                                <span style={{ color: 'var(--text-lo)' }}>{cfg.name}</span>
                                <span className="text-right" style={{ color: 'var(--text-hi)' }}>{(cfg.hit_rate * 100).toFixed(0)}%</span>
                                <span className="text-right" style={{ color: 'var(--text-hi)' }}>{cfg.mrr.toFixed(2)}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        <div className="rounded-2xl overflow-hidden" style={{ border: '1px solid var(--border-soft)' }}>
                          <div className="grid grid-cols-4 px-3 py-2 text-[10px] font-semibold uppercase" style={{ background: 'var(--bg-elevated)', color: 'var(--text-faint)' }}>
                            <span className="col-span-2">Question</span>
                            <span className="text-center">Hit</span>
                            <span className="text-right">MRR</span>
                          </div>
                          {evalData.per_question.map(r => (
                            <div key={r.id}>
                              <div
                                className="grid grid-cols-4 px-3 py-2 text-xs cursor-pointer transition-colors hover:bg-white/[0.03]"
                                style={{ borderTop: '1px solid var(--border-soft)' }}
                                onClick={() => setEvalSelectedQ(evalSelectedQ === r.id ? null : r.id)}
                              >
                                <span className="col-span-2 truncate" style={{ color: 'var(--text-lo)' }}>{r.id}</span>
                                <span className="text-center font-semibold" style={{ color: r.hit ? 'var(--success)' : 'var(--danger)' }}>
                                  {r.hit ? '✓' : '✗'}
                                </span>
                                <span className="text-right" style={{ color: 'var(--text-lo)' }}>{r.mrr.toFixed(2)}</span>
                              </div>
                              {evalSelectedQ === r.id && (
                                <div className="mx-3 mb-2 p-3 rounded-xl text-xs space-y-2" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-soft)' }}>
                                  <div>
                                    <div className="text-[10px] font-medium mb-0.5" style={{ color: 'var(--text-faint)' }}>Question</div>
                                    <div style={{ color: 'var(--text-hi)' }}>{r.question}</div>
                                  </div>
                                  <div>
                                    <div className="text-[10px] font-medium mb-0.5" style={{ color: 'var(--text-faint)' }}>Expected source</div>
                                    <div style={{ color: 'var(--text-hi)' }}>{(r.source_files || []).join(', ') || '—'}</div>
                                  </div>
                                  <div>
                                    <div className="text-[10px] font-medium mb-1" style={{ color: 'var(--text-faint)' }}>Retrieved</div>
                                    <div className="space-y-1">
                                      {(r.retrieved || []).map((chunk, i) => (
                                        <div key={i} className="flex items-center gap-1.5" style={{ color: chunk.hit ? 'var(--success)' : 'var(--text-faint)' }}>
                                          <span>{chunk.hit ? '✓' : '✗'}</span>
                                          <span>{chunk.file}{chunk.page && chunk.page !== '?' ? ` (p.${chunk.page})` : ''}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                        <p className="text-[10px]" style={{ color: 'var(--text-faint)' }}>{evalData.n_questions} questions · click a row to inspect retrieved chunks</p>
                      </div>
                    )}
                  </div>

                  {/* Answer Quality eval */}
                  <div className="pt-4" style={{ borderTop: '1px solid var(--border-soft)' }}>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-faint)' }}>Answer Quality</h3>
                      <Button size="sm" variant="outline" className="h-7 text-xs rounded-lg" onClick={runQualityEval} disabled={qualityLoading}>
                        {qualityLoading ? <><Loader2 className="w-3 h-3 mr-1.5 animate-spin" />Running…</> : 'Run quality eval'}
                      </Button>
                    </div>
                    {!qualityData && !qualityLoading && (
                      <p className="text-xs leading-relaxed" style={{ color: 'var(--text-faint)' }}>
                        Runs 15 LLM-graded questions through the full RAG pipeline and scores faithfulness, relevance, and correctness vs expected answers. Uses current provider ({provider === 'cloud' ? cloudModel : 'local'}).
                      </p>
                    )}
                    {qualityLoading && (
                      <div className="space-y-2">
                        <div className="skeleton h-16" />
                        <p className="text-xs italic" style={{ color: 'var(--text-faint)' }}>Generating and scoring answers — ~2–3 min for 15 questions…</p>
                      </div>
                    )}
                    {qualityData?.error && <p className="text-xs" style={{ color: 'var(--danger)' }}>{qualityData.error}</p>}
                    {qualityData && !qualityData.error && (
                      <div className="space-y-3">
                        <div className="grid grid-cols-3 gap-2">
                          {[['Faithfulness', qualityData.avg_faithfulness], ['Relevance', qualityData.avg_relevance], ['Correctness', qualityData.avg_correctness]].map(([label, val]) => (
                            <div key={label} className="glass rounded-xl p-2.5 text-center">
                              <div className="text-lg font-bold tabular-nums" style={{ color: evalColor(val) }}>{Math.round(val * 100)}%</div>
                              <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-faint)' }}>{label}</div>
                            </div>
                          ))}
                        </div>
                        <p className="text-[10px]" style={{ color: 'var(--text-faint)' }}>Model: {qualityData.model} · {qualityData.n_questions} questions</p>
                        <div className="rounded-2xl overflow-hidden" style={{ border: '1px solid var(--border-soft)' }}>
                          <div className="grid grid-cols-4 px-3 py-2 text-[10px] font-semibold uppercase" style={{ background: 'var(--bg-elevated)', color: 'var(--text-faint)' }}>
                            <span className="col-span-2">Question</span><span className="text-center">F/R</span><span className="text-right">Corr</span>
                          </div>
                          {qualityData.per_question.map(r => (
                            <div key={r.id}>
                              <div
                                className="grid grid-cols-4 px-3 py-2 text-xs cursor-pointer transition-colors hover:bg-white/[0.03]"
                                style={{ borderTop: '1px solid var(--border-soft)' }}
                                onClick={() => setQualitySelectedQ(qualitySelectedQ === r.id ? null : r.id)}
                              >
                                <span className="col-span-2 truncate" style={{ color: 'var(--text-lo)' }}>{r.id}</span>
                                <span className="text-center tabular-nums" style={{ color: evalColor(Math.min(r.faithfulness, r.relevance)) }}>{Math.round(r.faithfulness * 100)}/{Math.round(r.relevance * 100)}</span>
                                <span className="text-right tabular-nums font-medium" style={{ color: evalColor(r.correctness) }}>{Math.round(r.correctness * 100)}%</span>
                              </div>
                              {qualitySelectedQ === r.id && (
                                <div className="mx-3 mb-2 p-3 rounded-xl text-xs space-y-2" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-soft)' }}>
                                  <div><div className="text-[10px] font-medium mb-0.5" style={{ color: 'var(--text-faint)' }}>Question</div><div style={{ color: 'var(--text-hi)' }}>{r.question}</div></div>
                                  <div><div className="text-[10px] font-medium mb-0.5" style={{ color: 'var(--text-faint)' }}>Generated</div><div className="leading-relaxed" style={{ color: 'var(--text-lo)' }}>{r.generated}</div></div>
                                  <div><div className="text-[10px] font-medium mb-0.5" style={{ color: 'var(--text-faint)' }}>Expected</div><div className="leading-relaxed" style={{ color: 'var(--text-hi)' }}>{r.expected}</div></div>
                                  <div className="flex gap-3 pt-1">
                                    {[['Faith', r.faithfulness], ['Rel', r.relevance], ['Corr', r.correctness]].map(([k, v]) => (
                                      <span key={k} className="text-[10px] font-semibold" style={{ color: evalColor(v) }}>{k} {Math.round(v * 100)}%</span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </SheetContent>
        </Sheet>

        {/* ── File preview modal ── */}
        <AnimatePresence>
          {previewFile && (() => {
            const ext       = previewFile.split('.').pop().toLowerCase()
            const isImage   = ['png','jpg','jpeg','gif','bmp','webp'].includes(ext)
            const isPdfLike = ['pdf','pptx','docx','doc','xlsx','xls'].includes(ext)
            const hasText   = previewText !== null
            const { Icon, color } = fileMeta(previewFile)
            return (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 flex items-center justify-center p-4"
                style={{ background: 'rgba(9,9,11,0.7)', backdropFilter: 'blur(10px)' }}
                onClick={() => setPreviewFile(null)}
                role="dialog"
                aria-modal="true"
                aria-label={`Preview of ${previewFile}`}
              >
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: 16 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.96, y: 8 }}
                  transition={SPRING}
                  className="glass-strong rounded-3xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
                  onClick={e => e.stopPropagation()}
                >
                  <div className="flex items-center justify-between px-5 py-3.5 flex-shrink-0" style={{ borderBottom: '1px solid var(--border-soft)' }}>
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: `${color}14`, border: `1px solid ${color}26` }}>
                        <Icon className="w-3.5 h-3.5" style={{ color }} />
                      </div>
                      <span className="text-sm font-medium truncate" style={{ color: 'var(--text-hi)' }}>{previewFile}</span>
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      {previewBlobUrl && (
                        <motion.button
                          whileHover={{ scale: 1.04 }}
                          whileTap={{ scale: 0.96 }}
                          className="flex items-center gap-1.5 text-xs h-8 px-3 rounded-lg transition-colors hover:bg-white/[0.06]"
                          style={{ color: 'var(--text-lo)' }}
                          onClick={() => window.open(previewBlobUrl, '_blank')}
                        >
                          <ExternalLink className="w-3 h-3" /> Open in tab
                        </motion.button>
                      )}
                      <GhostIconButton title="Close preview" onClick={() => setPreviewFile(null)}>
                        <X className="w-4 h-4" />
                      </GhostIconButton>
                    </div>
                  </div>
                  <div className="flex-1 overflow-auto p-3 min-h-0">
                    {isPdfLike && (
                      previewBlobUrl
                        ? <iframe src={previewBlobUrl} title={previewFile} className="w-full h-full rounded-xl min-h-[500px]" style={{ border: '1px solid var(--border-soft)' }} />
                        : hasText ? <pre className="text-xs p-4 whitespace-pre-wrap" style={{ color: 'var(--text-lo)' }}>{previewText}</pre>
                          : <div className="space-y-2 p-4"><div className="skeleton h-6 w-1/2" /><div className="skeleton h-64" /><p className="text-xs text-center" style={{ color: 'var(--text-faint)' }}>Converting to PDF…</p></div>
                    )}
                    {isImage && (
                      previewBlobUrl
                        ? <img src={previewBlobUrl} alt={previewFile} className="max-w-full max-h-full mx-auto object-contain rounded-xl" />
                        : <div className="skeleton h-64 m-4" />
                    )}
                    {!isPdfLike && !isImage && hasText && (
                      <pre className="text-xs p-4 whitespace-pre-wrap leading-relaxed" style={{ color: 'var(--text-lo)' }}>{previewText}</pre>
                    )}
                    {!isPdfLike && !isImage && !hasText && (
                      <div className="space-y-2 p-4"><div className="skeleton h-6 w-1/3" /><div className="skeleton h-40" /></div>
                    )}
                  </div>
                </motion.div>
              </motion.div>
            )
          })()}
        </AnimatePresence>
      </div>
    </TooltipProvider>
  )
}

// ─── Root App ────────────────────────────────────────────────────────────────

function App() {
  const [authToken, setAuthToken]     = useState(() => localStorage.getItem('rag_token'))
  const [currentUser, setCurrentUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('rag_user')) } catch { return null }
  })

  useEffect(() => {
    document.documentElement.classList.add('dark')
  }, [])

  const handleAuth   = (token, user) => { setAuthToken(token); setCurrentUser(user) }
  const handleLogout = useCallback(() => {
    localStorage.removeItem('rag_token'); localStorage.removeItem('rag_user')
    setAuthToken(null); setCurrentUser(null)
  }, [])

  const authFetch = useCallback((url, options = {}) => {
    return fetch(url, {
      ...options,
      headers: { ...options.headers, ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}) }
    }).then(res => { if (res.status === 401) handleLogout(); return res })
  }, [authToken, handleLogout])

  if (!authToken || !currentUser) return <AuthScreen onAuth={handleAuth} />
  return <MainApp authFetch={authFetch} currentUser={currentUser} onLogout={handleLogout} />
}

export default App
