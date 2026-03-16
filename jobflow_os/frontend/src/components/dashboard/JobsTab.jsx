import { useState, useEffect, useCallback, useRef } from 'react'

const STATUS_PILL = {
  PENDING: 'bg-gray-100 text-gray-600',
  ENRICHED: 'bg-blue-100 text-blue-700',
  ENRICHMENT_FAILED: 'bg-red-100 text-red-600',
  STORY_READY: 'bg-purple-100 text-purple-700',
  IN_PROGRESS: 'bg-amber-100 text-amber-700',
  DONE: 'bg-green-100 text-green-700',
}

const API = 'http://localhost:8000'

const CONFIDENCE_COLOR = {
  HIGH:    'bg-green-100 text-green-700 border-green-300',
  MEDIUM:  'bg-amber-100 text-amber-700 border-amber-300',
  LOW:     'bg-red-100 text-red-600 border-red-300',
  UNKNOWN: 'bg-gray-100 text-gray-500 border-gray-200',
}

function EnrichedExpandedRow({ job }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const loaded = useRef(false)

  useEffect(() => {
    if (loaded.current) return
    loaded.current = true
    if (job.status !== 'ENRICHED' && job.status !== 'STORY_READY' && job.status !== 'DONE') return
    setLoading(true)
    fetch(`${API}/api/jobs/${job.id}/enrichment`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [job.id, job.status])

  // Base info always shown
  const baseInfo = (
    <div className="text-xs space-y-1 text-gray-600">
      {job.job_url && <div><span className="font-medium text-gray-500">URL:</span>{' '}
        <a href={job.job_url} className="text-blue-500 hover:underline" target="_blank" rel="noreferrer">{job.job_url}</a>
      </div>}
      {job.location && <div><span className="font-medium text-gray-500">Location:</span> {job.location}</div>}
      {job.notes && <div><span className="font-medium text-gray-500">Notes:</span> {job.notes}</div>}
    </div>
  )

  // Not enriched yet — just show base info
  if (job.status === 'PENDING' || job.status === 'ENRICHMENT_FAILED') {
    return <div className="px-6 py-3 bg-gray-50">{baseInfo}</div>
  }

  if (loading) {
    return (
      <div className="px-6 py-4 bg-blue-50 text-xs text-blue-600 italic">Loading enrichment data…</div>
    )
  }

  if (!data) {
    return <div className="px-6 py-3 bg-gray-50">{baseInfo}</div>
  }

  const confidence = data.enrichment_confidence || 'UNKNOWN'
  const confColor = CONFIDENCE_COLOR[confidence] || CONFIDENCE_COLOR.UNKNOWN

  return (
    <div className="bg-blue-50 border-t border-blue-100 px-6 py-4">

      {/* Header: what enrichment IS */}
      <div className="flex items-center gap-3 mb-3">
        <span className="text-xs font-semibold text-blue-800 uppercase tracking-wide">
          Enrichment — stored locally, used by agents
        </span>
        <span className={`text-xs font-medium border rounded px-2 py-0.5 ${confColor}`}>
          Confidence: {confidence}
        </span>
        <span className="text-xs text-gray-400 ml-auto">
          Enriched {data.enriched_at ? new Date(data.enriched_at).toLocaleString() : '—'}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Company summary */}
        {data.company_summary && (
          <div className="bg-white rounded border border-blue-200 p-3">
            <div className="text-xs font-semibold text-gray-500 mb-1">Company Summary</div>
            <div className="text-xs text-gray-700 leading-relaxed">{data.company_summary}</div>
          </div>
        )}

        {/* Team info */}
        {data.team_info && (
          <div className="bg-white rounded border border-blue-200 p-3">
            <div className="text-xs font-semibold text-gray-500 mb-1">Team Info</div>
            <div className="text-xs text-gray-700 leading-relaxed">{data.team_info}</div>
          </div>
        )}

        {/* Role signals */}
        {data.role_signals?.length > 0 && (
          <div className="bg-white rounded border border-blue-200 p-3">
            <div className="text-xs font-semibold text-gray-500 mb-1.5">Role Signals (what they want)</div>
            <div className="flex flex-wrap gap-1">
              {data.role_signals.map((s, i) => (
                <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">{s}</span>
              ))}
            </div>
          </div>
        )}

        {/* Fit indicators */}
        {data.fit_indicators?.length > 0 && (
          <div className="bg-white rounded border border-green-200 p-3">
            <div className="text-xs font-semibold text-gray-500 mb-1.5">Fit Indicators (your angles)</div>
            <div className="flex flex-wrap gap-1">
              {data.fit_indicators.map((s, i) => (
                <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-green-50 text-green-700 border border-green-200">{s}</span>
              ))}
            </div>
          </div>
        )}

        {/* Tech stack */}
        {data.tech_stack?.length > 0 && (
          <div className="bg-white rounded border border-blue-200 p-3">
            <div className="text-xs font-semibold text-gray-500 mb-1.5">Tech Stack</div>
            <div className="flex flex-wrap gap-1">
              {data.tech_stack.map((s, i) => (
                <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 border border-gray-200 font-mono">{s}</span>
              ))}
            </div>
          </div>
        )}

        {/* Contact targets */}
        {data.contact_targets?.length > 0 && (
          <div className="bg-white rounded border border-purple-200 p-3">
            <div className="text-xs font-semibold text-gray-500 mb-1.5">Who to Contact (titles)</div>
            <div className="flex flex-wrap gap-1">
              {data.contact_targets.map((s, i) => (
                <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">{s}</span>
              ))}
            </div>
          </div>
        )}

      </div>

      {/* Base info at bottom */}
      {(job.job_url || job.location || job.notes) && (
        <div className="mt-3 pt-3 border-t border-blue-200">{baseInfo}</div>
      )}
    </div>
  )
}

export default function JobsTab({ jobs, onReload }) {
  const [filter, setFilter] = useState('ALL')
  const [expanded, setExpanded] = useState(null)
  const [loadingJobs, setLoadingJobs] = useState(false)
  const [loadMsg, setLoadMsg] = useState('')
  const [enrichingIds, setEnrichingIds] = useState(new Set())
  const [enrichAllRunning, setEnrichAllRunning] = useState(false)

  const filtered = filter === 'ALL' ? jobs : jobs.filter(j => j.status === filter)

  // Poll status for in-progress enrichments
  useEffect(() => {
    if (enrichingIds.size === 0) return
    const interval = setInterval(async () => {
      const stillRunning = new Set()
      let anyDone = false
      for (const id of enrichingIds) {
        try {
          const r = await fetch(`${API}/api/jobs/${id}/enrich-status`)
          const d = await r.json()
          if (d.status === 'running') {
            stillRunning.add(id)
          } else {
            anyDone = true
          }
        } catch {
          stillRunning.add(id)
        }
      }
      setEnrichingIds(stillRunning)
      if (anyDone && onReload) onReload()
      if (stillRunning.size === 0) setEnrichAllRunning(false)
    }, 3000)
    return () => clearInterval(interval)
  }, [enrichingIds, onReload])

  async function handleLoadJobs() {
    setLoadingJobs(true)
    setLoadMsg('')
    try {
      const res = await fetch(`${API}/api/jobs/load`, { method: 'POST' })
      const data = await res.json()
      if (data.errors && data.errors.length > 0) {
        setLoadMsg(`Loaded ${data.loaded}, skipped ${data.skipped}, ${data.errors.length} errors`)
      } else {
        setLoadMsg(`Loaded ${data.loaded} new jobs, ${data.skipped} already existed`)
      }
      if (onReload) onReload()
    } catch {
      setLoadMsg('Error: could not reach backend')
    } finally {
      setLoadingJobs(false)
    }
  }

  async function handleEnrichOne(jobId) {
    setEnrichingIds(prev => new Set([...prev, jobId]))
    await fetch(`${API}/api/jobs/${jobId}/enrich`, { method: 'POST' })
  }

  async function handleEnrichAll() {
    setEnrichAllRunning(true)
    const res = await fetch(`${API}/api/jobs/enrich-all`, { method: 'POST' })
    const data = await res.json()
    setEnrichingIds(new Set(data.job_ids || []))
  }

  const pendingCount = jobs.filter(j => j.status === 'PENDING').length

  return (
    <div className="p-6">
      {/* Action bar */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <button
          onClick={handleLoadJobs}
          disabled={loadingJobs}
          className="text-sm px-4 py-1.5 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 font-medium"
        >
          {loadingJobs ? 'Loading…' : 'Load Jobs from Excel'}
        </button>

        {pendingCount > 0 && (
          <button
            onClick={handleEnrichAll}
            disabled={enrichAllRunning}
            className="text-sm px-4 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 font-medium"
          >
            {enrichAllRunning
              ? `Enriching ${enrichingIds.size} jobs…`
              : `Enrich All Pending (${pendingCount})`}
          </button>
        )}

        {loadMsg && <span className="text-sm text-green-600">{loadMsg}</span>}

        <div className="flex-1" />
        <select
          className="text-sm border border-gray-300 rounded px-3 py-1.5 focus:outline-none"
          value={filter}
          onChange={e => setFilter(e.target.value)}
        >
          <option value="ALL">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="ENRICHED">Enriched</option>
          <option value="STORY_READY">Story Ready</option>
          <option value="DONE">Done</option>
        </select>
        <span className="text-sm text-gray-400">{filtered.length} roles</span>
      </div>

      {/* Pipeline guide — show only when there are pending jobs */}
      {pendingCount > 0 && (
        <div className="mb-4 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
          <span className="font-semibold">Before running agents:</span> Jobs must be enriched first.
          Click <strong>Enrich All Pending</strong> to research each company (takes ~1–2 min per job).
          Status changes to <strong>ENRICHED</strong> when ready.
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-3 text-xs text-gray-500 font-medium">Company</th>
              <th className="text-left px-4 py-3 text-xs text-gray-500 font-medium">Role</th>
              <th className="text-left px-4 py-3 text-xs text-gray-500 font-medium">Status</th>
              <th className="text-left px-4 py-3 text-xs text-gray-500 font-medium">Priority</th>
              <th className="text-left px-4 py-3 text-xs text-gray-500 font-medium">Updated</th>
              <th className="text-left px-4 py-3 text-xs text-gray-500 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(job => (
              <>
                <tr
                  key={job.id}
                  onClick={() => setExpanded(expanded === job.id ? null : job.id)}
                  className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                >
                  <td className="px-4 py-3 font-medium text-gray-800">{job.company}</td>
                  <td className="px-4 py-3 text-gray-600">{job.role_title}</td>
                  <td className="px-4 py-3">
                    {enrichingIds.has(job.id) ? (
                      <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-blue-100 text-blue-700 animate-pulse">
                        enriching…
                      </span>
                    ) : (
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_PILL[job.status] || 'bg-gray-100 text-gray-600'}`}>
                        {job.status}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{job.priority}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {job.updated_at ? new Date(job.updated_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                    {job.status === 'PENDING' && !enrichingIds.has(job.id) && (
                      <button
                        onClick={() => handleEnrichOne(job.id)}
                        className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 font-medium"
                      >
                        Enrich
                      </button>
                    )}
                    {job.status === 'ENRICHMENT_FAILED' && !enrichingIds.has(job.id) && (
                      <button
                        onClick={() => handleEnrichOne(job.id)}
                        className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 font-medium"
                      >
                        Retry
                      </button>
                    )}
                    {enrichingIds.has(job.id) && (
                      <span className="text-xs text-blue-500 italic">working…</span>
                    )}
                  </td>
                </tr>
                {expanded === job.id && (
                  <tr key={`${job.id}-exp`}>
                    <td colSpan={6} className="px-0 py-0 border-b border-gray-200">
                      <EnrichedExpandedRow job={job} />
                    </td>
                  </tr>
                )}
              </>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400 text-sm">
                  No jobs found. Click "Load Jobs from Excel" to import your job list.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
