import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAgentStore } from '../hooks/useAgentStore'
import FloatingAgentWindow, { WIN_W, WIN_H } from '../components/command/FloatingAgentWindow'

const MAX_WINDOWS = 10
const WIN_GAP = 24

// Canvas-relative tile positions — 2 columns, no overlap
function tilePos(index) {
  const col = index % 2
  const row = Math.floor(index / 2)
  return {
    x: 20 + col * (WIN_W + WIN_GAP),
    y: 20 + row * (WIN_H / 2 + WIN_GAP),
  }
}

export default function CommandCenter() {
  const canvasRef = useRef(null)
  const [openWindows, setOpenWindows] = useState({})  // { agentId: { zIndex, pos } }
  const [topZ, setTopZ] = useState(100)
  const { send } = useWebSocket()
  const agents = useAgentStore(s => s.agents)

  // Auto-open a window for every new agent that appears in the store.
  // Single setOpenWindows call — avoids React batching bug where multiple
  // calls all see the same prev={} and stack every window at (20,20).
  useEffect(() => {
    const agentIds = Object.keys(agents)
    if (agentIds.length === 0) return
    setOpenWindows(prev => {
      let next = { ...prev }
      let nextIdx = Object.keys(prev).length
      for (const agentId of agentIds) {
        if (next[agentId]) continue                 // already open
        if (nextIdx >= MAX_WINDOWS) break
        next[agentId] = { zIndex: 100 + nextIdx, pos: tilePos(nextIdx) }
        nextIdx++
      }
      return next
    })
  }, [Object.keys(agents).join(',')])  // only re-run when agent IDs change

  function openWindow(agentId) {
    setOpenWindows(prev => {
      if (prev[agentId]) {
        // already open — just raise z-index
        const newZ = topZ + 1
        setTopZ(newZ)
        return { ...prev, [agentId]: { ...prev[agentId], zIndex: newZ } }
      }
      if (Object.keys(prev).length >= MAX_WINDOWS) return prev
      const idx = Object.keys(prev).length
      const newZ = topZ + 1
      setTopZ(newZ)
      return { ...prev, [agentId]: { zIndex: newZ, pos: tilePos(idx) } }
    })
  }

  function closeWindow(agentId) {
    setOpenWindows(prev => {
      const next = { ...prev }
      delete next[agentId]
      return next
    })
  }

  function focusWindow(agentId) {
    setTopZ(z => {
      const newZ = z + 1
      setOpenWindows(prev => ({
        ...prev,
        [agentId]: { ...prev[agentId], zIndex: newZ },
      }))
      return newZ
    })
  }

  const waitingAgents = Object.values(agents).filter(
    a => (a.pendingApproval || a.status === 'waiting') && !openWindows[a.id]
  )

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950 font-sans">
      {/* Icon sidebar */}
      <div className="w-14 flex-shrink-0 bg-gray-900 flex flex-col items-center py-4 gap-4 border-r border-gray-800">
        <div className="w-8 h-8 rounded-lg bg-purple-600 flex items-center justify-center">
          <span className="text-white text-xs font-bold">JF</span>
        </div>
        <div className="flex-1" />
        <Link
          to="/dashboard"
          className="w-8 h-8 rounded flex items-center justify-center text-gray-400 hover:text-white hover:bg-gray-700"
          title="Dashboard"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </Link>
      </div>

      {/* Agent roster */}
      <div className="w-56 flex-shrink-0 border-r border-gray-800 flex flex-col">
        <Roster agents={agents} openWindows={openWindows} onOpen={openWindow} send={send} />
      </div>

      {/* Canvas — all floating windows live here as absolute children */}
      <div ref={canvasRef} className="flex-1 relative overflow-hidden">
        {/* Dot-grid background */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(circle, #374151 1px, transparent 1px)',
            backgroundSize: '28px 28px',
          }}
        />

        {/* Empty state */}
        {Object.keys(openWindows).length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 pointer-events-none">
            <span className="text-gray-600 text-sm">Launch agents from the roster →</span>
            {waitingAgents.length > 0 && (
              <span className="text-amber-400 text-xs animate-pulse">
                ⚡ {waitingAgents.length} agent{waitingAgents.length > 1 ? 's' : ''} waiting for input
              </span>
            )}
          </div>
        )}

        {/* One window per agent */}
        {Object.entries(openWindows).map(([agentId, win]) => (
          <FloatingAgentWindow
            key={agentId}
            agent={agents[agentId]}
            canvasRef={canvasRef}
            send={send}
            onClose={() => closeWindow(agentId)}
            onFocus={() => focusWindow(agentId)}
            zIndex={win.zIndex}
            initialPos={win.pos}
          />
        ))}
      </div>
    </div>
  )
}

// ─── Roster ──────────────────────────────────────────────────────────────────

const DOT = {
  running: 'bg-green-500',
  waiting: 'bg-amber-400',
  paused: 'bg-red-400',
  idle: 'bg-gray-600',
}

function Roster({ agents, openWindows, onOpen, send }) {
  const [showForm, setShowForm] = useState(false)
  const [instructions, setInstructions] = useState('')
  const [availableJobs, setAvailableJobs] = useState([])
  const [selectedIds, setSelectedIds] = useState([])
  const [loading, setLoading] = useState(false)
  const [liAt, setLiAt] = useState('')
  const [jsessionid, setJsessionid] = useState('')
  const [showCookies, setShowCookies] = useState(false)
  const upsertAgent = useAgentStore(s => s.upsertAgent)
  const addMessage = useAgentStore(s => s.addMessage)

  useEffect(() => {
    if (!showForm) return
    setLoading(true)
    fetch('http://localhost:8000/api/jobs/')
      .then(r => r.json())
      .then(jobs => { setAvailableJobs(jobs); setLoading(false) })
      .catch(() => setLoading(false))
  }, [showForm])

  function toggleJob(id) {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  function handleStart() {
    if (selectedIds.length === 0) return
    const payload = { job_ids: selectedIds, standing_instructions: instructions }
    if (liAt.trim() && jsessionid.trim()) {
      payload.li_at = liAt.trim()
      payload.li_jsessionid = jsessionid.trim()
    }
    send('START_SESSION', payload)
    setShowForm(false)
    setSelectedIds([])
    setInstructions('')
    // keep cookies in state — reused next launch unless cleared
  }

  function injectTestAgents() {
    // Inject 2 fake agents so the UI can be tested without a backend
    const fakeAgents = [
      {
        id: `agent_1_${Date.now()}`,
        company: 'Apple',
        role: 'Product Lead',
        status: 'waiting',
        current_action: 'Waiting for approval',
        messages: [
          { id: 1, role: 'status', text: 'Loading context' },
          { id: 2, role: 'agent', text: 'Connected to LinkedIn. Searching for people at Apple...' },
          { id: 3, role: 'agent', text: '✓ Found Sarah Chen (Senior PM) — scored 8/10. Drafting message...' },
          { id: 4, role: 'agent', text: 'I found **Sarah Chen** — Senior Product Manager (score 8/10).\n\nHere\'s the draft above. Approve, skip, or type to guide me.' },
        ],
        pendingApproval: {
          contact_id: 1,
          agent_id: 'agent_1',
          session_id: 1,
          person: { name: 'Sarah Chen', title: 'Senior PM', linkedin_url: '#', mutual_connections: 0 },
          message_draft: "Your work on App Clips caught my eye — that's exactly the kind of frictionless onboarding I keep thinking about.\nCurious how you see vibe coding and AI-native workflows reshaping product building - would love to riff on this for a bit if you're open to it.",
          message_draft_b: '',
          recommended: 'A',
          relevance: 8,
          reason: 'Senior PM at Apple working on mobile UX — strong fit for AI product discussion.',
          context_snapshot: {},
        },
        unreadCount: 0,
      },
      {
        id: `agent_2_${Date.now() + 1}`,
        company: 'Google DeepMind',
        role: 'Research Engineer',
        status: 'running',
        current_action: 'Scoring candidates',
        messages: [
          { id: 1, role: 'status', text: 'Loading context' },
          { id: 2, role: 'agent', text: 'Connected to LinkedIn. Searching for people at Google DeepMind...' },
          { id: 3, role: 'agent', text: 'Found 12 candidates. Evaluating each one...' },
          { id: 4, role: 'agent', text: 'Reading profile: **James Park** — Research Engineer' },
        ],
        pendingApproval: null,
        unreadCount: 3,
      },
    ]
    fakeAgents.forEach(a => {
      upsertAgent(a.id, a)
    })
  }

  const agentList = Object.values(agents)

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between flex-shrink-0">
        <span className="text-gray-300 text-xs font-semibold uppercase tracking-wider">Agents</span>
        <div className="flex gap-1">
          {import.meta.env.DEV && (
            <button
              onClick={injectTestAgents}
              className="text-xs px-2 py-1 bg-gray-700 text-gray-300 rounded hover:bg-gray-600"
              title="Inject test agents"
            >
              🧪
            </button>
          )}
          <button
            onClick={() => setShowForm(v => !v)}
            className="text-xs px-2 py-1 bg-purple-600 text-white rounded hover:bg-purple-700"
          >
            {showForm ? '✕' : '+ New'}
          </button>
        </div>
      </div>

      {/* New session form */}
      {showForm && (
        <div className="border-b border-gray-800 bg-gray-800 overflow-y-auto flex-shrink-0" style={{ maxHeight: 280 }}>
          <div className="px-3 pt-2 pb-1 text-xs text-gray-400 uppercase tracking-wide">Select Jobs</div>
          {loading ? (
            <div className="px-4 py-2 text-xs text-gray-500">Loading…</div>
          ) : availableJobs.length === 0 ? (
            <div className="px-4 py-2 text-xs text-gray-500">No jobs found. Add jobs in the dashboard first.</div>
          ) : (
            <div className="px-2 pb-2 space-y-0.5">
              {availableJobs.map(job => (
                <label
                  key={job.id}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-gray-700 ${selectedIds.includes(job.id) ? 'bg-gray-700' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(job.id)}
                    onChange={() => toggleJob(job.id)}
                    className="accent-purple-500 flex-shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-gray-200 truncate font-medium">{job.company}</div>
                    <div className="text-xs text-gray-500 truncate">{job.role_title}</div>
                  </div>
                </label>
              ))}
            </div>
          )}
          <div className="px-3 pb-3 space-y-1.5">
            <textarea
              className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-gray-200 resize-none focus:outline-none focus:ring-1 focus:ring-purple-500"
              rows={2}
              placeholder="Standing instructions (optional)"
              value={instructions}
              onChange={e => setInstructions(e.target.value)}
            />

            {/* LinkedIn session cookies — collapsible */}
            <button
              onClick={() => setShowCookies(v => !v)}
              className="w-full text-left text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1 py-0.5"
            >
              <span>{showCookies ? '▾' : '▸'}</span>
              <span>LinkedIn cookies {liAt ? '✓' : '(optional — paste to avoid login challenge)'}</span>
            </button>

            {showCookies && (
              <div className="space-y-1 bg-gray-900 rounded p-2">
                <p className="text-xs text-gray-500">
                  Chrome → F12 → Application → Cookies → linkedin.com
                </p>
                <input
                  type="text"
                  value={liAt}
                  onChange={e => setLiAt(e.target.value)}
                  placeholder="li_at"
                  className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-gray-200 font-mono focus:outline-none focus:ring-1 focus:ring-amber-500"
                />
                <input
                  type="text"
                  value={jsessionid}
                  onChange={e => setJsessionid(e.target.value)}
                  placeholder="JSESSIONID  (e.g. ajax:123...)"
                  className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-gray-200 font-mono focus:outline-none focus:ring-1 focus:ring-amber-500"
                />
              </div>
            )}

            <button
              onClick={handleStart}
              disabled={selectedIds.length === 0}
              className="w-full text-xs py-1.5 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-40 font-medium"
            >
              Launch {selectedIds.length > 0 ? `${selectedIds.length} Agent${selectedIds.length > 1 ? 's' : ''}` : 'Agents'}
            </button>
          </div>
        </div>
      )}

      {/* Agent list */}
      <div className="flex-1 overflow-y-auto">
        {agentList.length === 0 ? (
          <div className="px-4 py-8 text-xs text-gray-600 text-center leading-relaxed">
            No active agents<br />
            <span className="text-gray-700">Click + New to launch</span>
          </div>
        ) : (
          agentList.map(agent => {
            const isWaiting = agent.pendingApproval || agent.status === 'waiting'
            const isOpen = !!openWindows[agent.id]
            return (
              <button
                key={agent.id}
                onClick={() => onOpen(agent.id)}
                className={`w-full text-left px-3 py-2.5 border-b border-gray-800 flex items-center gap-2.5 transition-colors ${isOpen ? 'bg-gray-800' : 'hover:bg-gray-800/60'}`}
              >
                <div className="relative flex-shrink-0 w-2.5 h-2.5">
                  {isWaiting && <div className="absolute inset-0 rounded-full bg-amber-400 animate-ping" />}
                  <div className={`w-2.5 h-2.5 rounded-full ${DOT[agent.status || 'idle']}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold text-gray-200 truncate">{agent.id}</div>
                  <div className="text-xs text-gray-500 truncate">{agent.company || 'Starting…'}</div>
                </div>
                {isWaiting && (
                  <span className="text-xs bg-amber-500 text-white px-1.5 py-0.5 rounded font-bold animate-pulse flex-shrink-0">!</span>
                )}
                {!isWaiting && (agent.unreadCount || 0) > 0 && (
                  <span className="text-xs bg-purple-600 text-white w-5 h-5 rounded-full flex items-center justify-center font-bold flex-shrink-0">
                    {agent.unreadCount > 9 ? '9+' : agent.unreadCount}
                  </span>
                )}
                {isOpen && <div className="w-1.5 h-1.5 rounded-full bg-purple-400 flex-shrink-0" />}
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
