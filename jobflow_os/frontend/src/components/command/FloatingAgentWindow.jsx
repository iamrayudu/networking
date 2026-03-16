import { useRef, useState, useEffect, useCallback } from 'react'
import AgentChat from './AgentChat'

export const WIN_W = 400
export const WIN_H = 520

const STATUS_COLOR = {
  running: 'bg-green-500',
  waiting: 'bg-amber-400',
  paused: 'bg-red-400',
  idle: 'bg-gray-400',
}

const HEADER_COLORS = [
  'bg-purple-700',
  'bg-blue-700',
  'bg-teal-700',
  'bg-rose-700',
  'bg-orange-700',
]

function agentIndex(agentId) {
  return (parseInt((agentId || '0').replace(/\D/g, ''), 10) || 0)
}

export default function FloatingAgentWindow({ agent, canvasRef, send, onClose, onFocus, zIndex, initialPos }) {
  const [pos, setPos] = useState(initialPos || { x: 20, y: 20 })
  const [minimized, setMinimized] = useState(false)
  const dragging = useRef(false)
  const dragOffset = useRef({ x: 0, y: 0 })

  const isWaiting = agent?.pendingApproval || agent?.status === 'waiting'
  const dotColor = STATUS_COLOR[agent?.status || 'idle']
  const headerColor = isWaiting
    ? 'bg-amber-500'
    : HEADER_COLORS[agentIndex(agent?.id) % HEADER_COLORS.length]

  const onTitleMouseDown = useCallback((e) => {
    if (e.target.closest('button')) return
    dragging.current = true
    dragOffset.current = { x: e.clientX - pos.x, y: e.clientY - pos.y }
    onFocus()
    e.preventDefault()
  }, [pos, onFocus])

  useEffect(() => {
    const onMouseMove = (e) => {
      if (!dragging.current) return
      const canvas = canvasRef?.current
      const maxX = canvas ? canvas.offsetWidth - WIN_W : window.innerWidth - WIN_W
      const maxY = canvas ? canvas.offsetHeight - 40 : window.innerHeight - 40
      setPos({
        x: Math.max(0, Math.min(maxX, e.clientX - dragOffset.current.x)),
        y: Math.max(0, Math.min(maxY, e.clientY - dragOffset.current.y)),
      })
    }
    const onMouseUp = () => { dragging.current = false }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [canvasRef])

  return (
    <div
      onMouseDown={onFocus}
      style={{
        position: 'absolute',
        left: pos.x,
        top: pos.y,
        zIndex,
        width: WIN_W,
        height: minimized ? 'auto' : WIN_H,
      }}
      className="flex flex-col rounded-xl shadow-2xl overflow-hidden select-none border border-white/10"
    >
      {/* Title bar — drag handle */}
      <div
        onMouseDown={onTitleMouseDown}
        className={`flex items-center gap-2 px-3 py-2.5 cursor-grab active:cursor-grabbing ${headerColor} transition-colors flex-shrink-0`}
      >
        {/* Status dot */}
        <div className="relative flex-shrink-0 w-2.5 h-2.5">
          {isWaiting && <div className="absolute inset-0 rounded-full bg-white animate-ping opacity-75" />}
          <div className={`w-2.5 h-2.5 rounded-full ${dotColor}`} />
        </div>

        {/* Agent id + company */}
        <div className="flex-1 min-w-0">
          <div className="text-white text-xs font-bold truncate leading-tight">
            {agent?.id || '…'}
          </div>
          {agent?.company && (
            <div className="text-white/70 text-xs truncate leading-tight">{agent.company}</div>
          )}
        </div>

        {isWaiting && (
          <span className="text-xs bg-white text-amber-600 font-bold px-1.5 py-0.5 rounded animate-pulse flex-shrink-0">
            Needs input
          </span>
        )}

        <button
          onClick={() => setMinimized(v => !v)}
          className="text-white/60 hover:text-white text-xs w-5 h-5 flex items-center justify-center rounded hover:bg-white/10 flex-shrink-0"
        >
          {minimized ? '▲' : '▼'}
        </button>
        <button
          onClick={onClose}
          className="text-white/60 hover:text-red-300 text-xs w-5 h-5 flex items-center justify-center rounded hover:bg-white/10 flex-shrink-0"
        >
          ✕
        </button>
      </div>

      {/* Chat body */}
      {!minimized && (
        <div className="flex-1 flex flex-col bg-white min-h-0">
          <AgentChat agent={agent} send={send} />
        </div>
      )}
    </div>
  )
}
