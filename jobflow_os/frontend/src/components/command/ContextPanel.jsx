import { useEffect, useState } from 'react'

export default function ContextPanel({ agent }) {
  const [decisions, setDecisions] = useState([])

  useEffect(() => {
    fetch('http://localhost:8000/api/memory/decisions?limit=5')
      .then(r => r.json())
      .then(setDecisions)
      .catch(() => {})
  }, [agent?.id])

  if (!agent) {
    return (
      <div className="h-full border-l border-gray-200 bg-white px-4 py-4 text-xs text-gray-400">
        No agent selected
      </div>
    )
  }

  const ACTION_COLORS = {
    APPROVE: 'bg-green-100 text-green-700',
    EDIT_APPROVE: 'bg-blue-100 text-blue-700',
    SKIP: 'bg-gray-100 text-gray-600',
  }

  return (
    <div className="h-full border-l border-gray-200 bg-white overflow-y-auto">
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Context</div>
      </div>

      {/* Role */}
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="text-xs font-semibold text-gray-400 uppercase mb-1">Role</div>
        {agent.company ? (
          <>
            <div className="text-sm font-medium text-gray-800">{agent.company}</div>
            <div className="text-xs text-gray-500">{agent.role}</div>
          </>
        ) : (
          <div className="text-xs text-gray-400">Not assigned</div>
        )}
      </div>

      {/* Session stats */}
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="text-xs font-semibold text-gray-400 uppercase mb-2">Session Stats</div>
        {agent.sessionStats || agent.stats ? (
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(agent.sessionStats || agent.stats || {}).map(([k, v]) => (
              <div key={k} className="bg-gray-50 rounded p-2">
                <div className="text-xs text-gray-400 capitalize">{k}</div>
                <div className="text-lg font-bold text-gray-700">{v}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-xs text-gray-400">No stats yet</div>
        )}
      </div>

      {/* Memory — past decisions */}
      <div className="px-4 py-3">
        <div className="text-xs font-semibold text-gray-400 uppercase mb-2">Recent Decisions</div>
        {decisions.length === 0 ? (
          <div className="text-xs text-gray-400">No decisions recorded yet</div>
        ) : (
          <div className="space-y-2">
            {decisions.map(d => (
              <div key={d.id} className="text-xs">
                <div className="flex items-center gap-1 mb-0.5">
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${ACTION_COLORS[d.action_type] || 'bg-gray-100 text-gray-600'}`}>
                    {d.action_type}
                  </span>
                </div>
                {d.inferred_preference && (
                  <div className="text-gray-600 pl-1">{d.inferred_preference}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
