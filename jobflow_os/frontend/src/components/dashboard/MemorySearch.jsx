import { useState } from 'react'

const ACTION_COLORS = {
  APPROVE: 'bg-green-100 text-green-700',
  EDIT_APPROVE: 'bg-blue-100 text-blue-700',
  SKIP: 'bg-gray-100 text-gray-600',
}

export default function MemorySearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)

  async function handleSearch() {
    if (!query.trim()) return
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/memory/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      const data = await res.json()
      setResults(data.results || [])
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-2xl">
      <div className="flex gap-2 mb-6">
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder="Search your memory... e.g. 'times I skipped recruiters'"
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-purple-400"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          {loading ? '...' : 'Search'}
        </button>
      </div>

      <div className="space-y-3">
        {results.map((r, i) => {
          const meta = r.metadata || {}
          const actionType = meta.action_type || ''
          return (
            <div key={i} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ACTION_COLORS[actionType] || 'bg-gray-100 text-gray-600'}`}>
                  {actionType || 'UNKNOWN'}
                </span>
                {meta.job_id && (
                  <span className="text-xs text-gray-400">job #{meta.job_id}</span>
                )}
              </div>
              <div className="text-sm text-gray-800 font-medium mb-1">{r.text}</div>
              {r.distance != null && (
                <div className="text-xs text-gray-400">relevance: {(1 - r.distance).toFixed(2)}</div>
              )}
            </div>
          )
        })}
        {results.length === 0 && query && !loading && (
          <div className="text-sm text-gray-400">No results found.</div>
        )}
      </div>
    </div>
  )
}
