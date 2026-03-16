import { useState } from 'react'

export default function ReportsTab() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)

  async function generateSummary() {
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/reports/summary', { method: 'POST' })
      const data = await res.json()
      setSummary(data.summary || [])
    } catch {
      setSummary(['Error generating summary'])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-2xl space-y-4">
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={generateSummary}
          disabled={loading}
          className="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          {loading ? 'Generating...' : 'Generate Session Summary'}
        </button>
        <a
          href="http://localhost:8000/api/reports/contacts.csv"
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          download
        >
          Export Contacts CSV
        </a>
        <a
          href="http://localhost:8000/api/reports/outreach.csv"
          className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
          download
        >
          Export Outreach CSV
        </a>
      </div>

      {summary && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 mt-4">
          <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
            {summary.join('\n')}
          </pre>
        </div>
      )}
    </div>
  )
}
