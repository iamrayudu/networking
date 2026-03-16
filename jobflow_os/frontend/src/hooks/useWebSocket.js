import { useEffect, useCallback } from 'react'
import { useAgentStore } from './useAgentStore'

const WS_URL = 'ws://localhost:8000/ws'

// Module-level singleton — shared across all hook calls, persists across page navigation
let _ws = null

function handleMessage(event) {
  const store = useAgentStore.getState()
  try {
    const { type, payload } = JSON.parse(event.data)
    const aid = payload?.agent_id

    switch (type) {
      case 'AGENT_BRIEFING':
      case 'AGENT_MESSAGE':
        store.addMessage(aid, { role: 'agent', text: payload.message, phase: payload.phase })
        store.upsertAgent(aid, { id: aid })
        break
      case 'APPROVAL_REQUEST':
        store.setPendingApproval(aid, payload)
        store.addMessage(aid, { role: 'approval', data: payload })
        break
      case 'AGENT_STATUS':
        store.setAgentStatus(aid, payload.status, payload.current_action)
        store.upsertAgent(aid, { id: aid, company: payload.company, role: payload.role })
        if (payload.current_action) {
          store.addMessage(aid, { role: 'status', text: payload.current_action })
        }
        break
      case 'COOKIE_REFRESH_REQUIRED':
        store.addMessage(aid, { role: 'cookie_refresh', data: payload })
        store.upsertAgent(aid, { id: aid, status: 'waiting' })
        break
      case 'COOKIE_REFRESH_RESULT':
        // Broadcast result to all open agent windows via a system message
        Object.keys(store.agents).forEach(agentId => {
          store.addMessage(agentId, {
            role: 'system',
            text: payload.message,
          })
        })
        break
      case 'PREFERENCE_APPLIED':
        store.addMessage(aid, {
          role: 'system',
          text: `Applying preference: ${payload.preference_rule}`,
        })
        break
      case 'SESSION_UPDATE':
        store.setKpis(payload)
        break
      case 'PHASE_COMPLETE':
        store.addMessage(aid, {
          role: 'agent',
          text: `Phase complete. ${JSON.stringify(payload.summary_stats)}`,
        })
        break
      case 'ERROR':
        store.addMessage(aid, { role: 'system', text: `Error: ${payload.message}` })
        break
      case 'SESSION_COMPLETE':
        store.addMessage('system', { role: 'system', text: payload.summary })
        break
      default:
        break
    }
  } catch (e) {
    console.error('WS message parse error', e)
  }
}

function connect() {
  if (_ws && (_ws.readyState === WebSocket.CONNECTING || _ws.readyState === WebSocket.OPEN)) return
  _ws = new WebSocket(WS_URL)
  _ws.onopen = () => console.log('WS connected')
  _ws.onclose = () => {
    console.log('WS disconnected — reconnecting in 3s')
    setTimeout(connect, 3000)
  }
  _ws.onerror = (e) => console.error('WS error', e)
  _ws.onmessage = handleMessage
}

export function useWebSocket() {
  useEffect(() => {
    connect()
  }, [])

  const send = useCallback((type, payload) => {
    if (_ws?.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify({ type, payload }))
    } else {
      console.warn('WS not open — message dropped', type)
    }
  }, [])

  return { send }
}
