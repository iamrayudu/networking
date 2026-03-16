import { useState, useEffect, useRef } from 'react'

const API = 'http://localhost:8000'

const STATUS_COLOR = {
  SUCCESS:  'text-green-700 bg-green-50',
  FAILED:   'text-red-700 bg-red-50',
  SKIPPED:  'text-gray-600 bg-gray-50',
  ERROR:    'text-red-800 bg-red-100 font-semibold',
  INFO:     'text-blue-700 bg-blue-50',
}

const SEVERITY_COLOR = {
  CRITICAL: 'text-red-800 bg-red-100 font-bold',
  HIGH:     'text-red-700 bg-red-50 font-semibold',
  MEDIUM:   'text-amber-700 bg-amber-50',
  LOW:      'text-gray-600 bg-gray-50',
}

const SOURCE_BADGE = {
  LOG:     'bg-blue-100 text-blue-700',
  FAILURE: 'bg-red-100 text-red-700',
}

function ts(raw) {
  if (!raw) return '—'
  const d = new Date(raw)
  return isNaN(d) ? raw : d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function Badge({ label, color }) {
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${color}`}>
      {label}
    </span>
  )
}

// ─── Timeline Tab ────────────────────────────────────────────────────────────
function TimelineView({ sessions }) {
  const [sessionId, setSessionId] = useState('')
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const intervalRef = useRef(null)

  async function load() {
    setLoading(true)
    const q = sessionId ? `?session_id=${sessionId}&limit=500` : '?limit=500'
    try {
      const r = await fetch(`${API}/api/logs/timeline${q}`)
      setRows(await r.json())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [sessionId])

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(load, 3000)
    } else {
      clearInterval(intervalRef.current)
    }
    return () => clearInterval(intervalRef.current)
  }, [autoRefresh, sessionId])

  return (
    <div>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <select
          className="text-sm border border-gray-300 rounded px-3 py-1.5"
          value={sessionId}
          onChange={e => setSessionId(e.target.value)}
        >
          <option value="">All Sessions</option>
          {sessions.map(s => (
            <option key={s.id} value={s.id}>
              Session {s.id} — {s.started_at ? new Date(s.started_at).toLocaleString() : '?'}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={e => setAutoRefresh(e.target.checked)}
            className="accent-purple-600"
          />
          Live (3s)
        </label>
        <button onClick={load} className="text-xs px-3 py-1.5 bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
          Refresh
        </button>
        {loading && <span className="text-xs text-gray-400 italic">loading…</span>}
        <span className="text-xs text-gray-400 ml-auto">{rows.length} events</span>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-left">
              <th className="px-3 py-2 text-gray-500 font-medium w-20">Time</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-20">Agent</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-16">Source</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-20">Level</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-36">Event</th>
              <th className="px-3 py-2 text-gray-500 font-medium">Detail</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-24">Company</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  No events yet. Start a session to see live logs here.
                </td>
              </tr>
            ) : rows.map((r, i) => (
              <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-3 py-1.5 font-mono text-gray-400">{ts(r.timestamp)}</td>
                <td className="px-3 py-1.5 text-gray-600">{r.agent_id || '—'}</td>
                <td className="px-3 py-1.5">
                  <Badge label={r.event_source} color={SOURCE_BADGE[r.event_source] || 'bg-gray-100 text-gray-600'} />
                </td>
                <td className="px-3 py-1.5">
                  <Badge
                    label={r.level}
                    color={
                      r.event_source === 'FAILURE'
                        ? (SEVERITY_COLOR[r.level] || 'bg-gray-100 text-gray-600')
                        : (STATUS_COLOR[r.level] || 'bg-gray-100 text-gray-600')
                    }
                  />
                </td>
                <td className="px-3 py-1.5 font-medium text-gray-700">{r.event_type}</td>
                <td className="px-3 py-1.5 text-gray-500 max-w-xs truncate" title={r.detail}>{r.detail || '—'}</td>
                <td className="px-3 py-1.5 text-gray-500">{r.company || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Failures Tab ─────────────────────────────────────────────────────────────
function FailuresView() {
  const [rows, setRows] = useState([])
  const [severity, setSeverity] = useState('')
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    const q = severity ? `?severity=${severity}` : ''
    try {
      const r = await fetch(`${API}/api/logs/failures${q}`)
      setRows(await r.json())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [severity])

  const COUNTS = ['CRITICAL','HIGH','MEDIUM','LOW'].map(s => ({
    s, count: rows.filter(r => r.severity === s).length
  }))

  return (
    <div>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <select
          className="text-sm border border-gray-300 rounded px-3 py-1.5"
          value={severity}
          onChange={e => setSeverity(e.target.value)}
        >
          <option value="">All Severities</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>
        <button onClick={load} className="text-xs px-3 py-1.5 bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
          Refresh
        </button>
        {loading && <span className="text-xs text-gray-400 italic">loading…</span>}
        {/* Severity pill counts */}
        <div className="flex gap-2 ml-auto">
          {COUNTS.map(({ s, count }) => count > 0 && (
            <span key={s} className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEVERITY_COLOR[s]}`}>
              {s}: {count}
            </span>
          ))}
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="py-12 text-center text-gray-400 text-sm">No failures recorded.</div>
      ) : (
        <div className="space-y-2">
          {rows.map((r, i) => (
            <div key={i} className={`rounded-lg border px-4 py-3 ${
              r.severity === 'CRITICAL' ? 'border-red-300 bg-red-50' :
              r.severity === 'HIGH'     ? 'border-red-200 bg-red-50' :
              r.severity === 'MEDIUM'   ? 'border-amber-200 bg-amber-50' :
              'border-gray-200 bg-white'
            }`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge label={r.severity} color={SEVERITY_COLOR[r.severity] || ''} />
                  <span className="font-semibold text-sm text-gray-800">{r.failure_type}</span>
                  <span className="text-xs text-gray-500">→ {r.action_taken}</span>
                </div>
                <span className="text-xs text-gray-400 flex-shrink-0">{ts(r.timestamp)}</span>
              </div>
              <div className="mt-1.5 flex items-center gap-4 text-xs text-gray-500 flex-wrap">
                {r.company && <span>Company: <strong className="text-gray-700">{r.company}</strong></span>}
                {r.agent_id && <span>Agent: <strong className="text-gray-700">{r.agent_id}</strong></span>}
                {r.session_id && <span>Session: {r.session_id}</span>}
              </div>
              {r.detail && (
                <div className="mt-1.5 text-xs text-gray-600 font-mono bg-white bg-opacity-60 rounded px-2 py-1 border border-gray-200">
                  {r.detail}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Agent Log Tab ────────────────────────────────────────────────────────────
function AgentLogView({ sessions }) {
  const [rows, setRows] = useState([])
  const [filterStatus, setFilterStatus] = useState('')
  const [filterSession, setFilterSession] = useState('')
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const intervalRef = useRef(null)

  async function load() {
    setLoading(true)
    const params = new URLSearchParams({ limit: 300 })
    if (filterStatus) params.set('status', filterStatus)
    if (filterSession) params.set('session_id', filterSession)
    try {
      const r = await fetch(`${API}/api/logs/?${params}`)
      setRows(await r.json())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filterStatus, filterSession])

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(load, 3000)
    } else {
      clearInterval(intervalRef.current)
    }
    return () => clearInterval(intervalRef.current)
  }, [autoRefresh, filterStatus, filterSession])

  const byStatus = rows.reduce((acc, r) => {
    acc[r.status] = (acc[r.status] || 0) + 1
    return acc
  }, {})

  return (
    <div>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <select
          className="text-sm border border-gray-300 rounded px-3 py-1.5"
          value={filterSession}
          onChange={e => setFilterSession(e.target.value)}
        >
          <option value="">All Sessions</option>
          {sessions.map(s => (
            <option key={s.id} value={s.id}>Session {s.id}</option>
          ))}
        </select>
        <select
          className="text-sm border border-gray-300 rounded px-3 py-1.5"
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="SUCCESS">SUCCESS</option>
          <option value="FAILED">FAILED</option>
          <option value="SKIPPED">SKIPPED</option>
          <option value="ERROR">ERROR</option>
        </select>
        <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
          <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} className="accent-purple-600" />
          Live (3s)
        </label>
        <button onClick={load} className="text-xs px-3 py-1.5 bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
          Refresh
        </button>
        {loading && <span className="text-xs text-gray-400 italic">loading…</span>}
        {/* Status summary pills */}
        <div className="flex gap-2 ml-auto flex-wrap">
          {Object.entries(byStatus).map(([s, count]) => (
            <span key={s} className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[s] || 'bg-gray-100 text-gray-600'}`}>
              {s}: {count}
            </span>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-left">
              <th className="px-3 py-2 text-gray-500 font-medium w-20">Time</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-20">Agent</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-20">Status</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-36">Action</th>
              <th className="px-3 py-2 text-gray-500 font-medium">Detail</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-28">Company</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  No agent logs yet.
                </td>
              </tr>
            ) : rows.map((r, i) => (
              <tr key={i} className={`border-b border-gray-50 hover:bg-gray-50 ${r.status === 'ERROR' || r.status === 'FAILED' ? 'bg-red-50' : ''}`}>
                <td className="px-3 py-1.5 font-mono text-gray-400">{ts(r.timestamp)}</td>
                <td className="px-3 py-1.5 text-gray-600">{r.agent_id || '—'}</td>
                <td className="px-3 py-1.5">
                  <Badge label={r.status} color={STATUS_COLOR[r.status] || 'bg-gray-100 text-gray-600'} />
                </td>
                <td className="px-3 py-1.5 font-medium text-gray-700">{r.action}</td>
                <td className="px-3 py-1.5 text-gray-500 max-w-xs truncate" title={r.detail}>{r.detail || '—'}</td>
                <td className="px-3 py-1.5 text-gray-500">{r.company || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Enrichment Log Tab ───────────────────────────────────────────────────────
function EnrichmentView() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/logs/enrichment`)
      setRows(await r.json())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const STATUS_COLOR_MAP = {
    PENDING: 'bg-gray-100 text-gray-600',
    ENRICHED: 'bg-green-100 text-green-700',
    ENRICHMENT_FAILED: 'bg-red-100 text-red-700',
    STORY_READY: 'bg-purple-100 text-purple-700',
    DONE: 'bg-blue-100 text-blue-700',
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <button onClick={load} className="text-xs px-3 py-1.5 bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
          Refresh
        </button>
        {loading && <span className="text-xs text-gray-400 italic">loading…</span>}
        <span className="text-xs text-gray-400 ml-auto">
          {rows.filter(r => r.has_enrichment).length} / {rows.length} enriched
        </span>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-left">
              <th className="px-3 py-2 text-gray-500 font-medium">Company</th>
              <th className="px-3 py-2 text-gray-500 font-medium">Role</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-28">Status</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-20">Enriched</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-20">Enriched At</th>
              <th className="px-3 py-2 text-gray-500 font-medium w-28">Updated</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-3 py-2 font-medium text-gray-800">{r.company}</td>
                <td className="px-3 py-2 text-gray-600">{r.role_title}</td>
                <td className="px-3 py-2">
                  <Badge label={r.status} color={STATUS_COLOR_MAP[r.status] || 'bg-gray-100 text-gray-600'} />
                </td>
                <td className="px-3 py-2">
                  {r.has_enrichment
                    ? <span className="text-green-600 font-medium">✓ Yes</span>
                    : <span className="text-gray-400">—</span>}
                </td>
                <td className="px-3 py-2 text-gray-500">{r.enriched_at ? new Date(r.enriched_at).toLocaleTimeString() : '—'}</td>
                <td className="px-3 py-2 text-gray-400">
                  {r.updated_at ? new Date(r.updated_at).toLocaleDateString() : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Live File Log Tab ────────────────────────────────────────────────────────
function LiveFileLogView() {
  const [lines, setLines] = useState([])
  const [lineCount, setLineCount] = useState(200)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [exists, setExists] = useState(true)
  const intervalRef = useRef(null)
  const bottomRef = useRef(null)

  async function load() {
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/logs/file?lines=${lineCount}`)
      const data = await r.json()
      setLines(data.lines || [])
      setTotal(data.total || 0)
      setExists(data.exists !== false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [lineCount])

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(load, 2000)
    } else {
      clearInterval(intervalRef.current)
    }
    return () => clearInterval(intervalRef.current)
  }, [autoRefresh, lineCount])

  // Auto-scroll to bottom when auto-refresh is on
  useEffect(() => {
    if (autoRefresh && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [lines])

  function lineColor(line) {
    if (!line) return 'text-gray-400'
    const l = line.toLowerCase()
    if (l.includes('| error') || l.includes('captcha') || l.includes('critical')) return 'text-red-400'
    if (l.includes('| warning') || l.includes('failed') || l.includes('warn')) return 'text-amber-400'
    if (l.includes('| info') && (l.includes('sent') || l.includes('passed') || l.includes('done') || l.includes('ready'))) return 'text-green-400'
    if (l.includes('| info')) return 'text-gray-300'
    if (l.includes('| debug')) return 'text-gray-500'
    return 'text-gray-300'
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <select
          className="text-sm border border-gray-300 rounded px-3 py-1.5"
          value={lineCount}
          onChange={e => setLineCount(Number(e.target.value))}
        >
          <option value={100}>Last 100 lines</option>
          <option value={200}>Last 200 lines</option>
          <option value={500}>Last 500 lines</option>
          <option value={1000}>Last 1000 lines</option>
        </select>
        <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={e => setAutoRefresh(e.target.checked)}
            className="accent-purple-600"
          />
          Live (2s)
        </label>
        <button onClick={load} className="text-xs px-3 py-1.5 bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
          Refresh
        </button>
        {loading && <span className="text-xs text-gray-400 italic">loading…</span>}
        <span className="text-xs text-gray-400 ml-auto">
          {exists ? `showing ${lines.length} of ${total} total lines` : 'log file not found'}
        </span>
      </div>

      {!exists ? (
        <div className="py-12 text-center text-gray-400 text-sm">
          <div className="text-2xl mb-2">📄</div>
          <div>logs/jobflow.log not found.</div>
          <div className="text-xs mt-1">Start the backend — logging begins automatically.</div>
        </div>
      ) : (
        <div className="bg-gray-950 rounded-lg border border-gray-700 overflow-auto" style={{ maxHeight: '60vh' }}>
          <pre className="text-xs font-mono px-4 py-3 whitespace-pre-wrap break-all leading-5">
            {lines.length === 0 ? (
              <span className="text-gray-500">No log lines yet.</span>
            ) : lines.map((line, i) => (
              <div key={i} className={lineColor(line)}>
                {line || '\u00A0'}
              </div>
            ))}
            <div ref={bottomRef} />
          </pre>
        </div>
      )}
    </div>
  )
}

// ─── Flow Debug View ─────────────────────────────────────────────────────────
// Live binary pipeline trace: every agent, every function, every pass/fail.

function parseFuncAction(action) {
  if (!action) return { func: '', actionName: '' }
  const i = action.indexOf(' → ')
  if (i < 0) return { func: '', actionName: action }
  const funcFull = action.substring(0, i)
  const dot = funcFull.lastIndexOf('.')
  return { func: dot >= 0 ? funcFull.substring(dot + 1) : funcFull, actionName: action.substring(i + 3) }
}

const STAGE_ORDER = ['init', 'search', 'profile', 'score', 'draft', 'approval', 'send']
const STAGE_META = {
  init:     { label: 'Initialize', short: 'INIT',    color: 'blue'   },
  search:   { label: 'Search',     short: 'SEARCH',  color: 'indigo' },
  profile:  { label: 'Profile',    short: 'PROFILE', color: 'violet' },
  score:    { label: 'Score',      short: 'SCORE',   color: 'amber'  },
  draft:    { label: 'Draft',      short: 'DRAFT',   color: 'orange' },
  approval: { label: 'Approval',   short: 'APPROVE', color: 'pink'   },
  send:     { label: 'Send',       short: 'SEND',    color: 'green'  },
}
const STAGE_COLORS = {
  blue:   { bg: 'bg-blue-100',   border: 'border-blue-300',   text: 'text-blue-800',   dot: 'bg-blue-500',   faint: 'bg-blue-50'   },
  indigo: { bg: 'bg-indigo-100', border: 'border-indigo-300', text: 'text-indigo-800', dot: 'bg-indigo-500', faint: 'bg-indigo-50' },
  violet: { bg: 'bg-violet-100', border: 'border-violet-300', text: 'text-violet-800', dot: 'bg-violet-500', faint: 'bg-violet-50' },
  amber:  { bg: 'bg-amber-100',  border: 'border-amber-300',  text: 'text-amber-800',  dot: 'bg-amber-500',  faint: 'bg-amber-50'  },
  orange: { bg: 'bg-orange-100', border: 'border-orange-300', text: 'text-orange-800', dot: 'bg-orange-500', faint: 'bg-orange-50' },
  pink:   { bg: 'bg-pink-100',   border: 'border-pink-300',   text: 'text-pink-800',   dot: 'bg-pink-500',   faint: 'bg-pink-50'   },
  green:  { bg: 'bg-green-100',  border: 'border-green-300',  text: 'text-green-800',  dot: 'bg-green-500',  faint: 'bg-green-50'  },
}

function classifyStage(entry) {
  const { func, actionName } = parseFuncAction(entry.action)
  const f = func.toLowerCase()
  const a = (actionName + ' ' + (entry.action || '')).toUpperCase()
  if (f === 'start' || a.includes('CONTEXT') || a.includes('CHROME') || a.includes('BRIEFING') || a.includes('LOGIN')) return 'init'
  if (f.includes('search') || a.includes('GUARD_PASSED') || a.includes('GUARD_FAILED') || a.includes('SEARCH')) return 'search'
  if (f.includes('read_profile') || a.includes('EXTRACT') || a.includes('NAVIGATE') || a.includes('PAGE_GUARD') || a.includes('PROFILE') || a.includes('UNREADABLE') || a.includes('MINIMAL')) return 'profile'
  if (f.includes('score') || a.includes('SCORING') || a.includes('SCORE')) return 'score'
  if (f.includes('draft') || a.includes('DRAFT')) return 'draft'
  if (f.includes('request_approval') || a.includes('WAITING') || a.includes('DECISION') || a.includes('APPROVAL')) return 'approval'
  if (f.includes('send') || a.includes('SENT') || a.includes('SEND_FAILED')) return 'send'
  return 'other'
}

function OutcomeChip({ status }) {
  if (status === 'SUCCESS') return <span className="inline-flex items-center gap-0.5 text-xs font-bold text-green-700 bg-green-100 border border-green-300 rounded-full px-2 py-0.5">✓ PASS</span>
  if (status === 'FAILED')  return <span className="inline-flex items-center gap-0.5 text-xs font-bold text-red-700 bg-red-100 border border-red-300 rounded-full px-2 py-0.5">✗ FAIL</span>
  if (status === 'ERROR')   return <span className="inline-flex items-center gap-0.5 text-xs font-bold text-red-800 bg-red-100 border border-red-400 rounded-full px-2 py-0.5">✗ ERROR</span>
  if (status === 'SKIPPED') return <span className="inline-flex items-center gap-0.5 text-xs font-medium text-gray-600 bg-gray-100 border border-gray-300 rounded-full px-2 py-0.5">→ SKIP</span>
  return <span className="text-xs text-gray-300 px-1">·</span>
}

function FlowNode({ entry, isLast }) {
  const { func, actionName } = parseFuncAction(entry.action)
  const stage = classifyStage(entry)
  const meta = STAGE_META[stage]
  const colors = meta ? STAGE_COLORS[meta.color] : STAGE_COLORS.blue
  const isFail = entry.status === 'FAILED' || entry.status === 'ERROR'
  const isSkip = entry.status === 'SKIPPED'

  return (
    <div className="flex gap-0 min-h-0">
      {/* Left rail: dot + vertical line */}
      <div className="flex flex-col items-center w-8 flex-shrink-0">
        <div className="w-px bg-gray-200 h-3 flex-shrink-0" />
        <div className={`w-3.5 h-3.5 rounded-full flex-shrink-0 z-10 ${
          isFail ? 'bg-red-500 ring-2 ring-red-200' : isSkip ? 'bg-gray-300' : (colors?.dot || 'bg-gray-400')
        }`} />
        {!isLast && <div className="w-px bg-gray-200 flex-1 min-h-3" />}
      </div>

      {/* Card */}
      <div className={`flex-1 ml-2 mb-1 rounded-lg border px-3 py-2.5 ${
        isFail ? 'bg-red-50 border-red-200' :
        isSkip ? 'bg-gray-50 border-gray-200' :
        `${colors?.faint} ${colors?.border}`
      }`}>
        {/* Header row */}
        <div className="flex items-center gap-2 flex-wrap">
          {meta && (
            <span className={`text-xs font-semibold px-1.5 py-0.5 rounded border flex-shrink-0 ${colors?.bg} ${colors?.text} ${colors?.border}`}>
              {meta.short}
            </span>
          )}
          <code className="text-xs font-mono flex-shrink-0">
            {func && <span className="text-gray-400">{func}</span>}
            {func && <span className="text-gray-300 mx-0.5">→</span>}
            <span className={`font-semibold ${isFail ? 'text-red-700' : 'text-gray-800'}`}>
              {actionName || entry.action}
            </span>
          </code>
          <div className="ml-auto flex items-center gap-2 flex-shrink-0">
            <OutcomeChip status={entry.status} />
            <span className="text-xs text-gray-400 font-mono">{ts(entry.timestamp)}</span>
          </div>
        </div>

        {/* Detail */}
        {entry.detail && (
          <div className={`mt-1 text-xs font-mono leading-relaxed break-all ${isFail ? 'text-red-700 font-medium' : 'text-gray-600'}`}>
            {entry.detail}
          </div>
        )}

        {/* Fail annotation */}
        {isFail && (
          <div className="mt-1.5 flex items-center gap-1 text-xs text-red-500">
            <span className="font-mono">↪</span>
            <span>Pipeline blocked here — flow does not continue past this step</span>
          </div>
        )}
      </div>
    </div>
  )
}

function PipelineBar({ entries }) {
  // Compute highest-interest status per stage
  const stageStatus = {}
  for (const e of entries) {
    const s = classifyStage(e)
    if (s === 'other') continue
    const cur = stageStatus[s]
    const isBad = v => v === 'FAILED' || v === 'ERROR'
    if (!cur) stageStatus[s] = e.status
    else if (!isBad(cur) && isBad(e.status)) stageStatus[s] = e.status
    else if (cur === 'SUCCESS' && e.status === 'SKIPPED') stageStatus[s] = e.status
  }
  return (
    <div className="flex items-center gap-0.5 flex-wrap">
      {STAGE_ORDER.map((k, idx) => {
        const meta = STAGE_META[k]
        const colors = STAGE_COLORS[meta.color]
        const status = stageStatus[k]
        const icon = !status ? '–' : status === 'SUCCESS' ? '✓' : (status === 'FAILED' || status === 'ERROR') ? '✗' : '→'
        const cls = !status
          ? 'bg-gray-100 border-gray-200 text-gray-400'
          : (status === 'FAILED' || status === 'ERROR')
            ? 'bg-red-100 border-red-300 text-red-700'
            : status === 'SKIPPED'
              ? 'bg-gray-100 border-gray-300 text-gray-600'
              : `${colors.bg} ${colors.border} ${colors.text}`
        return (
          <div key={k} className="flex items-center">
            <span className={`text-xs font-medium border rounded px-1.5 py-0.5 ${cls}`}>{icon} {meta.short}</span>
            {idx < STAGE_ORDER.length - 1 && <span className="text-gray-200 text-xs mx-0.5">›</span>}
          </div>
        )
      })}
    </div>
  )
}

function AgentFlowSection({ agentId, entries, company, roleTitle }) {
  const [open, setOpen] = useState(true)
  const fail = entries.filter(e => e.status === 'FAILED' || e.status === 'ERROR').length
  const skip = entries.filter(e => e.status === 'SKIPPED').length
  const pass = entries.filter(e => e.status === 'SUCCESS').length
  return (
    <div className="mb-5 rounded-xl border border-gray-200 overflow-hidden">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 text-left"
        onClick={() => setOpen(o => !o)}
      >
        <span className="font-mono text-sm font-semibold text-gray-700">{agentId}</span>
        {company && <span className="text-sm text-gray-500">{company}{roleTitle ? ` — ${roleTitle}` : ''}</span>}
        <div className="flex gap-1.5 ml-2">
          {pass > 0 && <span className="text-xs px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">✓ {pass}</span>}
          {skip > 0 && <span className="text-xs px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium">→ {skip}</span>}
          {fail > 0 && <span className="text-xs px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">✗ {fail}</span>}
        </div>
        <div className="ml-auto flex items-center gap-3">
          <PipelineBar entries={entries} />
          <span className="text-gray-400 text-xs">{open ? '▲' : '▼'}</span>
        </div>
      </button>
      {open && (
        <div className="px-4 pt-3 pb-2">
          {entries.map((e, i) => (
            <FlowNode key={e.id ?? i} entry={e} isLast={i === entries.length - 1} />
          ))}
        </div>
      )}
    </div>
  )
}

function FlowDebugView({ sessions }) {
  const [rows, setRows] = useState([])
  const [sessionId, setSessionId] = useState('')
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const intervalRef = useRef(null)

  async function load() {
    setLoading(true)
    const params = new URLSearchParams({ limit: 500 })
    if (sessionId) params.set('session_id', sessionId)
    try {
      const r = await fetch(`${API}/api/logs/?${params}`)
      const data = await r.json()
      setRows([...data].reverse()) // oldest-first so flow reads top→bottom
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [sessionId])
  useEffect(() => {
    if (autoRefresh) intervalRef.current = setInterval(load, 3000)
    else clearInterval(intervalRef.current)
    return () => clearInterval(intervalRef.current)
  }, [autoRefresh, sessionId])

  // Group by agent_id, preserve insertion order
  const groups = {}
  const order = []
  for (const row of rows) {
    const key = row.agent_id || 'unknown'
    if (!groups[key]) { groups[key] = { entries: [], company: row.company, roleTitle: row.role_title }; order.push(key) }
    groups[key].entries.push(row)
  }

  return (
    <div>
      {/* Controls */}
      <div className="flex items-center gap-3 mb-5 flex-wrap">
        <select className="text-sm border border-gray-300 rounded px-3 py-1.5" value={sessionId} onChange={e => setSessionId(e.target.value)}>
          <option value="">All Sessions</option>
          {sessions.map(s => (
            <option key={s.id} value={s.id}>Session {s.id} — {s.started_at ? new Date(s.started_at).toLocaleString() : '?'}</option>
          ))}
        </select>
        <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
          <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} className="accent-purple-600" />
          Live (3s)
        </label>
        <button onClick={load} className="text-xs px-3 py-1.5 bg-gray-100 text-gray-700 rounded hover:bg-gray-200">Refresh</button>
        {loading && <span className="text-xs text-gray-400 italic">loading…</span>}
        <span className="text-xs text-gray-400 ml-auto">{rows.length} entries · {order.length} agents</span>
      </div>

      {/* Stage colour legend + outcome key */}
      <div className="flex flex-wrap gap-2 mb-5">
        {STAGE_ORDER.map(k => {
          const m = STAGE_META[k]; const c = STAGE_COLORS[m.color]
          return <span key={k} className={`text-xs px-2 py-0.5 rounded border font-medium ${c.bg} ${c.text} ${c.border}`}>{m.label}</span>
        })}
        <span className="text-xs px-2 py-0.5 rounded border bg-green-100 text-green-700 border-green-300 font-bold ml-4">✓ PASS</span>
        <span className="text-xs px-2 py-0.5 rounded border bg-red-100 text-red-700 border-red-300 font-bold">✗ FAIL</span>
        <span className="text-xs px-2 py-0.5 rounded border bg-gray-100 text-gray-600 border-gray-300 font-medium">→ SKIP</span>
      </div>

      {/* Static pipeline map — all possible paths */}
      <div className="mb-6 rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-3">
        <div className="text-xs text-gray-500 font-semibold mb-2 uppercase tracking-wide">All Possible Paths</div>
        <div className="flex flex-wrap items-center gap-x-1 gap-y-1 text-xs font-mono mb-3">
          <span className="text-gray-400">START</span>
          <span className="text-gray-300">→</span>
          <span className="font-bold text-blue-700">INIT</span>
          <span className="text-gray-300">→</span>
          <span className="font-bold text-indigo-700">SEARCH</span>
          <span className="text-gray-300">→</span>
          <span className="text-gray-400 italic">[per person]</span>
          <span className="text-gray-300">→</span>
          <span className="font-bold text-violet-700">PROFILE</span>
          <span className="text-gray-300">→</span>
          <span className="font-bold text-amber-700">SCORE</span>
          <span className="text-gray-300">→</span>
          <span className="font-bold text-orange-700">DRAFT</span>
          <span className="text-gray-300">→</span>
          <span className="font-bold text-pink-700">APPROVAL</span>
          <span className="text-gray-300">→</span>
          <span className="font-bold text-green-700">SEND</span>
          <span className="text-gray-300">→</span>
          <span className="text-gray-400">DONE</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-1 text-xs text-gray-500">
          <span><span className="font-semibold text-red-600">INIT✗</span> → missing profile / enrichment → STOP agent</span>
          <span><span className="font-semibold text-red-600">SEARCH✗</span> → zero results → ask user to widen filter</span>
          <span><span className="font-semibold text-red-600">PROFILE✗</span> → CAPTCHA → STOP ALL agents immediately</span>
          <span><span className="font-semibold text-amber-600">PROFILE⟳</span> → logged out → PAUSE + ask you to re-login</span>
          <span><span className="font-semibold text-gray-500">PROFILE→</span> → private / too sparse → skip this person</span>
          <span><span className="font-semibold text-gray-500">SCORE→</span> → score too low → skip this person</span>
          <span><span className="font-semibold text-gray-500">APPROVAL→</span> → rejected / timed out → skip this person</span>
          <span><span className="font-semibold text-gray-500">SEND→</span> → already connected → mark contacted + skip</span>
        </div>
      </div>

      {/* Per-agent flow traces */}
      {order.length === 0 ? (
        <div className="py-20 text-center text-gray-400">
          <div className="text-5xl mb-4 opacity-20">⬡</div>
          <div className="font-medium text-sm">No agent activity yet.</div>
          <div className="text-xs mt-1">Start a session — the full execution trace appears here, step by step.</div>
        </div>
      ) : order.map(agentId => (
        <AgentFlowSection
          key={agentId}
          agentId={agentId}
          entries={groups[agentId].entries}
          company={groups[agentId].company}
          roleTitle={groups[agentId].roleTitle}
        />
      ))}
    </div>
  )
}

// ─── Root LogsTab ─────────────────────────────────────────────────────────────
const SUBTABS = ['Flow', 'Timeline', 'Agent Log', 'Failures', 'Enrichment', 'File Log']

export default function LogsTab() {
  const [active, setActive] = useState('Flow')
  const [sessions, setSessions] = useState([])

  useEffect(() => {
    fetch(`${API}/api/logs/sessions`)
      .then(r => r.json())
      .then(setSessions)
      .catch(() => {})
  }, [])

  return (
    <div className="p-6">
      {/* Sub-tab nav */}
      <div className="flex gap-0 border-b border-gray-200 mb-5">
        {SUBTABS.map(t => (
          <button
            key={t}
            onClick={() => setActive(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              active === t
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {active === 'Flow'       && <FlowDebugView sessions={sessions} />}
      {active === 'Timeline'   && <TimelineView sessions={sessions} />}
      {active === 'Agent Log'  && <AgentLogView sessions={sessions} />}
      {active === 'Failures'   && <FailuresView />}
      {active === 'Enrichment' && <EnrichmentView />}
      {active === 'File Log'   && <LiveFileLogView />}
    </div>
  )
}
