import { useAgentStore } from '../../hooks/useAgentStore'

const metrics = [
  { key: 'jobs', label: 'Jobs Loaded' },
  { key: 'enriched', label: 'Enriched' },
  { key: 'stories', label: 'Stories Ready' },
  { key: 'contacts', label: 'Contacts Found' },
  { key: 'sent', label: 'Sent' },
  { key: 'replied', label: 'Replies' },
]

export default function KPIBar({ extra }) {
  const kpis = useAgentStore(s => s.kpis)
  const combined = { ...kpis, ...extra }

  return (
    <div className="grid grid-cols-6 gap-0 border-b border-gray-200 bg-white">
      {metrics.map((m, i) => (
        <div
          key={m.key}
          className={`px-6 py-4 ${i < metrics.length - 1 ? 'border-r border-gray-200' : ''}`}
        >
          <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">{m.label}</div>
          <div className="text-2xl font-bold text-gray-800">{combined[m.key] ?? 0}</div>
        </div>
      ))}
    </div>
  )
}
