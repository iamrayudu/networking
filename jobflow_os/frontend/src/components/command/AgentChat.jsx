import { useEffect, useRef, useState } from 'react'
import ApprovalCard from './ApprovalCard'
import CookieRefreshCard from './CookieRefreshCard'
import { useAgentStore } from '../../hooks/useAgentStore'

export default function AgentChat({ agent, send }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)
  // ALL hooks must be before any conditional return
  const clearUnread = useAgentStore(s => s.clearUnread)
  const addMessage = useAgentStore(s => s.addMessage)

  useEffect(() => {
    if (agent?.id) clearUnread(agent.id)
  }, [agent?.id, agent?.messages?.length])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [agent?.messages?.length])

  // Guard AFTER all hooks
  if (!agent) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
        Select an agent to view chat
      </div>
    )
  }

  function handleSend() {
    if (!input.trim()) return
    const text = input.trim()
    addMessage(agent.id, { role: 'user', text })
    send('USER_REPLY', { agent_id: agent.id, message: text, broadcast: false })
    setInput('')
  }

  const statusColor = {
    running: 'bg-green-500',
    waiting: 'bg-amber-400',
    paused: 'bg-red-400',
    idle: 'bg-gray-400',
  }[agent.status || 'idle']

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-gray-100 px-3 py-2 flex items-center justify-between bg-white flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${statusColor}`} />
          <span className="font-semibold text-gray-800 text-xs truncate">{agent.id}</span>
          {agent.current_action && (
            <span className="text-xs text-gray-400 truncate hidden sm:block">{agent.current_action}</span>
          )}
        </div>
        <div className="flex gap-1 flex-shrink-0">
          {agent.status !== 'paused' ? (
            <button
              onClick={() => send('PAUSE_AGENT', { agent_id: agent.id })}
              className="px-2 py-0.5 text-xs bg-amber-100 text-amber-700 rounded hover:bg-amber-200"
            >
              Pause
            </button>
          ) : (
            <button
              onClick={() => send('RESUME_AGENT', { agent_id: agent.id })}
              className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
            >
              Resume
            </button>
          )}
          <button
            onClick={() => send('STOP_AGENT', { agent_id: agent.id })}
            className="px-2 py-0.5 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
          >
            Stop
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2 bg-gray-50 min-h-0">
        {(agent.messages || []).map((msg) => {
          if (msg.role === 'agent') {
            return (
              <div key={msg.id} className="flex justify-start">
                <div className="max-w-[85%] bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-800 shadow-sm leading-relaxed">
                  {msg.text}
                </div>
              </div>
            )
          }
          if (msg.role === 'user') {
            return (
              <div key={msg.id} className="flex justify-end">
                <div className="max-w-[85%] bg-purple-600 text-white rounded-lg px-3 py-2 text-xs shadow-sm">
                  {msg.text}
                </div>
              </div>
            )
          }
          if (msg.role === 'status') {
            return (
              <div key={msg.id} className="flex items-center gap-2 py-0.5">
                <div className="flex-1 h-px bg-gray-200" />
                <span className="text-xs text-gray-400 whitespace-nowrap flex-shrink-0">⚙ {msg.text}</span>
                <div className="flex-1 h-px bg-gray-200" />
              </div>
            )
          }
          if (msg.role === 'system') {
            return (
              <div key={msg.id} className="flex justify-center">
                <div className="text-xs text-gray-400 italic">{msg.text}</div>
              </div>
            )
          }
          if (msg.role === 'approval') {
            return (
              <div key={msg.id}>
                <ApprovalCard data={msg.data} send={send} />
              </div>
            )
          }
          if (msg.role === 'cookie_refresh') {
            return (
              <div key={msg.id}>
                <CookieRefreshCard send={send} />
              </div>
            )
          }
          return null
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 px-3 py-2 bg-white flex gap-2 flex-shrink-0">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Reply to agent…"
          className="flex-1 border border-gray-300 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-purple-400"
        />
        <button
          onClick={handleSend}
          className="px-3 py-1.5 text-xs bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium"
        >
          Send
        </button>
      </div>
    </div>
  )
}
