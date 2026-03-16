import { useState } from 'react'

export default function CookieRefreshCard({ send }) {
  const [liAt, setLiAt] = useState('')
  const [jsessionid, setJsessionid] = useState('')
  const [submitted, setSubmitted] = useState(false)

  function handleSubmit() {
    if (!liAt.trim() || !jsessionid.trim()) return
    send('REFRESH_COOKIES', { li_at: liAt.trim(), li_jsessionid: jsessionid.trim() })
    setSubmitted(true)
  }

  return (
    <div className="border border-amber-300 bg-amber-50 rounded-lg p-3 text-xs space-y-2">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-amber-600 text-base">⚠️</span>
        <span className="font-semibold text-amber-800">LinkedIn session expired</span>
      </div>

      {submitted ? (
        <div className="text-green-700 font-medium">
          ✓ Cookies submitted — agent is resuming...
        </div>
      ) : (
        <>
          <p className="text-gray-600 leading-relaxed">
            Paste fresh cookies from your browser to resume without restarting.
            <br />
            Chrome → F12 → Application → Cookies → <code className="bg-gray-100 px-1 rounded">linkedin.com</code>
          </p>

          <div className="space-y-1.5">
            <label className="block">
              <span className="text-gray-500 font-medium">li_at</span>
              <textarea
                rows={2}
                value={liAt}
                onChange={e => setLiAt(e.target.value)}
                placeholder="Paste li_at cookie value..."
                className="mt-0.5 w-full border border-gray-300 rounded px-2 py-1 text-xs font-mono resize-none focus:outline-none focus:ring-1 focus:ring-amber-400"
              />
            </label>

            <label className="block">
              <span className="text-gray-500 font-medium">JSESSIONID</span>
              <input
                type="text"
                value={jsessionid}
                onChange={e => setJsessionid(e.target.value)}
                placeholder='e.g. ajax:1234567890123456789'
                className="mt-0.5 w-full border border-gray-300 rounded px-2 py-1 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-amber-400"
              />
            </label>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!liAt.trim() || !jsessionid.trim()}
            className="w-full py-1.5 bg-amber-500 text-white rounded font-medium hover:bg-amber-600 disabled:opacity-40 transition-colors"
          >
            Refresh &amp; Resume
          </button>
        </>
      )}
    </div>
  )
}
