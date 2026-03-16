import { useState } from 'react'

const STATUS_PILL = {
  FOUND: 'bg-gray-100 text-gray-600',
  PENDING_APPROVAL: 'bg-amber-100 text-amber-700',
  SENT: 'bg-green-100 text-green-700',
  SKIPPED: 'bg-red-100 text-red-600',
  REPLIED: 'bg-blue-100 text-blue-700',
}

export default function ContactsTab({ contacts }) {
  const [filterCompany, setFilterCompany] = useState('ALL')
  const [filterStatus, setFilterStatus] = useState('ALL')
  const [expanded, setExpanded] = useState(null)

  const companies = ['ALL', ...new Set(contacts.map(c => c.company).filter(Boolean))]

  const filtered = contacts.filter(c => {
    if (filterCompany !== 'ALL' && c.company !== filterCompany) return false
    if (filterStatus !== 'ALL' && c.status !== filterStatus) return false
    return true
  })

  return (
    <div className="p-6">
      <div className="flex gap-3 mb-4">
        <select
          className="text-sm border border-gray-300 rounded px-3 py-1.5 focus:outline-none"
          value={filterCompany}
          onChange={e => setFilterCompany(e.target.value)}
        >
          {companies.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select
          className="text-sm border border-gray-300 rounded px-3 py-1.5 focus:outline-none"
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
        >
          <option value="ALL">All Statuses</option>
          <option value="FOUND">Found</option>
          <option value="PENDING_APPROVAL">Pending</option>
          <option value="SENT">Sent</option>
          <option value="SKIPPED">Skipped</option>
          <option value="REPLIED">Replied</option>
        </select>
        <span className="text-sm text-gray-400 self-center">{filtered.length} contacts</span>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-3 text-xs text-gray-500 font-medium">Name</th>
              <th className="text-left px-4 py-3 text-xs text-gray-500 font-medium">Title</th>
              <th className="text-left px-4 py-3 text-xs text-gray-500 font-medium">Company</th>
              <th className="text-left px-4 py-3 text-xs text-gray-500 font-medium">Score</th>
              <th className="text-left px-4 py-3 text-xs text-gray-500 font-medium">Status</th>
              <th className="text-left px-4 py-3 text-xs text-gray-500 font-medium">Date</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(c => (
              <>
                <tr
                  key={c.id}
                  onClick={() => setExpanded(expanded === c.id ? null : c.id)}
                  className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                >
                  <td className="px-4 py-3 font-medium text-gray-800">{c.full_name}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{c.title}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{c.company}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-bold ${c.relevance_score >= 8 ? 'text-green-600' : c.relevance_score >= 5 ? 'text-amber-600' : 'text-red-500'}`}>
                      {c.relevance_score}/10
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_PILL[c.status] || 'bg-gray-100 text-gray-600'}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {c.contacted_at ? new Date(c.contacted_at).toLocaleDateString() : '—'}
                  </td>
                </tr>
                {expanded === c.id && (
                  <tr key={`${c.id}-exp`} className="bg-blue-50">
                    <td colSpan={6} className="px-6 py-3 text-xs space-y-1 text-gray-600">
                      {c.linkedin_url && <div><span className="font-medium">LinkedIn:</span> <a href={c.linkedin_url} className="text-blue-500 hover:underline" target="_blank">{c.linkedin_url}</a></div>}
                      {c.relevance_reason && <div><span className="font-medium">Reason:</span> {c.relevance_reason}</div>}
                      {c.invite_message && <div><span className="font-medium">Message:</span> <em>{c.invite_message}</em></div>}
                    </td>
                  </tr>
                )}
              </>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400 text-sm">No contacts found</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
