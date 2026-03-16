import { useState, useEffect } from 'react'

const STATUS_DOT = {
  running: 'bg-green-500',
  waiting: 'bg-amber-400',
  paused: 'bg-red-400',
  idle: 'bg-gray-300',
}

export default function AgentRoster({ agents, selectedId, onSelect, send }) {
  const [showForm, setShowForm] = useState(false)
  const [instructions, setInstructions] = useState('')
  const [availableJobs, setAvailableJobs] = useState([])
  const [selectedJobIds, setSelectedJobIds] = useState([])
  const [loadingJobs, setLoadingJobs] = useState(false)

  const agentList = Object.values(agents || {})

  useEffect(() => {
    if (showForm) {
      setLoadingJobs(true)
      fetch('http://localhost:8000/api/jobs/')
        .then(r => r.json())
        .then(jobs => { setAvailableJobs(jobs); setLoadingJobs(false) })
        .catch(() => setLoadingJobs(false))
    }
  }, [showForm])

  function toggleJob(id) {
    setSelectedJobIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  function handleStart() {
    if (selectedJobIds.length === 0) return
    send('START_SESSION', { job_ids: selectedJobIds, standing_instructions: instructions })
    setShowForm(false)
    setSelectedJobIds([])
    setInstructions('')
  }

  const STATUS_BADGE = {
    PENDING: 'bg-gray-100 text-gray-500',
    ENRICHED: 'bg-blue-100 text-blue-600',
    STORY_READY: 'bg-purple-100 text-purple-600',
    DONE: 'bg-green-100 text-green-600',
  }

  return (
    <div className="flex flex-col h-full border-r border-gray-200 bg-white">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <span className="font-semibold text-gray-700 text-sm">Agents</span>
        <button
          onClick={() => setShowForm(v => !v)}
          className="text-xs px-2 py-1 bg-purple-600 text-white rounded hover:bg-purple-700"
        >
          {showForm ? '✕ Close' : '+ Start'}
        </button>
      </div>

      {/* Start session form */}
      {showForm && (
        <div className="border-b border-gray-200 bg-purple-50 overflow-y-auto max-h-96">
          <div className="px-4 pt-3 pb-1 text-xs font-semibold text-gray-600 uppercase tracking-wide">
            Select Jobs
          </div>

          {loadingJobs ? (
            <div className="px-4 py-3 text-xs text-gray-400">Loading jobs…</div>
          ) : availableJobs.length === 0 ? (
            <div className="px-4 py-3 text-xs text-gray-400">
              No jobs loaded. Go to Dashboard → Jobs → Load Jobs from Excel first.
            </div>
          ) : (
            <div className="px-3 pb-2 space-y-1">
              {availableJobs.map(job => (
                <label
                  key={job.id}
                  className={`flex items-start gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-purple-100 ${
                    selectedJobIds.includes(job.id) ? 'bg-purple-100' : ''
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedJobIds.includes(job.id)}
                    onChange={() => toggleJob(job.id)}
                    className="mt-0.5 flex-shrink-0 accent-purple-600"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-gray-800 truncate">{job.company}</div>
                    <div className="text-xs text-gray-500 truncate">{job.role_title}</div>
                  </div>
                  <span className={`text-xs px-1.5 py-0.5 rounded-full flex-shrink-0 ${STATUS_BADGE[job.status] || 'bg-gray-100 text-gray-500'}`}>
                    {job.status}
                  </span>
                </label>
              ))}
            </div>
          )}

          <div className="px-4 pt-2 pb-1 text-xs font-semibold text-gray-600 uppercase tracking-wide">
            Standing Instructions
          </div>
          <div className="px-3 pb-3">
            <textarea
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs resize-none focus:outline-none focus:ring-1 focus:ring-purple-400 bg-white"
              rows={2}
              placeholder="Optional: e.g. Prefer 2nd degree only, skip recruiters"
              value={instructions}
              onChange={e => setInstructions(e.target.value)}
            />
            <button
              onClick={handleStart}
              disabled={selectedJobIds.length === 0}
              className="w-full mt-2 text-xs py-1.5 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-40 disabled:cursor-not-allowed font-medium"
            >
              Launch {selectedJobIds.length > 0 ? `${selectedJobIds.length} Agent${selectedJobIds.length > 1 ? 's' : ''}` : 'Agents'}
            </button>
          </div>
        </div>
      )}

      {/* Agent list */}
      <div className="flex-1 overflow-y-auto">
        {agentList.length === 0 ? (
          <div className="px-4 py-6 text-xs text-gray-400 text-center">No active agents</div>
        ) : (
          agentList.map(agent => (
            <button
              key={agent.id}
              onClick={() => onSelect(agent.id)}
              className={`w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-gray-50 flex items-center gap-3 ${
                selectedId === agent.id ? 'border-l-2 border-l-purple-600 bg-purple-50' : ''
              }`}
            >
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_DOT[agent.status || 'idle']}`} />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold text-gray-800 truncate">{agent.id}</div>
                <div className="text-xs text-gray-400 truncate">
                  {agent.company && agent.role
                    ? `${agent.company} · ${agent.role}`.slice(0, 24)
                    : 'Idle'}
                </div>
              </div>
              {agent.unreadCount > 0 && (
                <div className="flex-shrink-0 w-5 h-5 rounded-full bg-purple-600 text-white text-xs flex items-center justify-center font-bold">
                  {agent.unreadCount > 9 ? '9+' : agent.unreadCount}
                </div>
              )}
            </button>
          ))
        )}
      </div>
    </div>
  )
}
