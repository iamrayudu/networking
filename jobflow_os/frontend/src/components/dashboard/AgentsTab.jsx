import { useNavigate } from 'react-router-dom'
import { useAgentStore } from '../../hooks/useAgentStore'
import { useWebSocket } from '../../hooks/useWebSocket'

const STATUS_PILL = {
  running: 'bg-green-100 text-green-700',
  waiting: 'bg-amber-100 text-amber-700',
  paused: 'bg-red-100 text-red-700',
  idle: 'bg-gray-100 text-gray-500',
}

export default function AgentsTab() {
  const agents = useAgentStore(s => s.agents)
  const { send } = useWebSocket()
  const navigate = useNavigate()
  const agentList = Object.values(agents)

  if (agentList.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 gap-3 text-gray-400 text-sm">
        <div>No active agents.</div>
        <button
          onClick={() => navigate('/command')}
          className="text-xs px-3 py-1.5 bg-purple-600 text-white rounded hover:bg-purple-700"
        >
          Go to Command Center to start one
        </button>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 p-6">
      {agentList.map(agent => (
        <div key={agent.id} className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="font-semibold text-gray-800 text-sm">{agent.id}</div>
              <div className="text-xs text-gray-400">{agent.company} · {agent.role}</div>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_PILL[agent.status || 'idle']}`}>
              {agent.status || 'idle'}
            </span>
          </div>

          {agent.current_action && (
            <div className="text-xs text-gray-500 mb-3 italic">{agent.current_action}</div>
          )}

          {/* Stats */}
          {agent.stats && (
            <div className="flex gap-3 mb-3">
              {Object.entries(agent.stats).map(([k, v]) => (
                <div key={k} className="text-center">
                  <div className="text-sm font-bold text-gray-700">{v}</div>
                  <div className="text-xs text-gray-400 capitalize">{k}</div>
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => navigate(`/command?agent=${agent.id}`)}
              className="text-xs px-2 py-1 bg-purple-600 text-white rounded hover:bg-purple-700 font-medium"
            >
              View Chat →
            </button>
            <button
              onClick={() => send('PAUSE_AGENT', { agent_id: agent.id })}
              className="text-xs px-2 py-1 bg-amber-100 text-amber-700 rounded hover:bg-amber-200"
            >
              Pause
            </button>
            <button
              onClick={() => send('RESUME_AGENT', { agent_id: agent.id })}
              className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200"
            >
              Resume
            </button>
            <button
              onClick={() => send('STOP_AGENT', { agent_id: agent.id })}
              className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"
            >
              Stop
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
