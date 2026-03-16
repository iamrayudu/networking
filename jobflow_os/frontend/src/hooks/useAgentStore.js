import { create } from 'zustand'

// Always returns a safe agent base — never missing messages or unreadCount
function base(existing) {
  return { messages: [], unreadCount: 0, ...existing }
}

export const useAgentStore = create((set, get) => ({
  agents: {},
  // agents[agent_id] = {
  //   id, job_id, company, role, status, messages: [],
  //   pendingApproval: null, unreadCount: 0, sessionStats: {}
  // }

  upsertAgent: (agent_id, data) => set(state => ({
    agents: {
      ...state.agents,
      [agent_id]: { ...base(state.agents[agent_id]), ...data },
    },
  })),

  addMessage: (agent_id, message) => set(state => {
    const agent = base(state.agents[agent_id])
    return {
      agents: {
        ...state.agents,
        [agent_id]: {
          ...agent,
          messages: [...agent.messages, { ...message, id: Date.now() }],
          unreadCount: agent.unreadCount + 1,
        },
      },
    }
  }),

  clearUnread: (agent_id) => set(state => ({
    agents: {
      ...state.agents,
      [agent_id]: { ...base(state.agents[agent_id]), unreadCount: 0 },
    },
  })),

  setAgentStatus: (agent_id, status, current_action) => set(state => ({
    agents: {
      ...state.agents,
      [agent_id]: { ...base(state.agents[agent_id]), status, current_action },
    },
  })),

  setPendingApproval: (agent_id, approval) => set(state => ({
    agents: {
      ...state.agents,
      [agent_id]: { ...base(state.agents[agent_id]), pendingApproval: approval },
    },
  })),

  clearPendingApproval: (agent_id) => set(state => ({
    agents: {
      ...state.agents,
      [agent_id]: { ...base(state.agents[agent_id]), pendingApproval: null },
    },
  })),

  kpis: { jobs: 0, contacts: 0, sent: 0, replied: 0 },
  setKpis: (kpis) => set({ kpis }),
}))
