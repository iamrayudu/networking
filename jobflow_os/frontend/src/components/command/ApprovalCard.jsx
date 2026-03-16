import { useState } from 'react'

export default function ApprovalCard({ data, send }) {
  const recommended = data.recommended || 'A'
  const [activeDraft, setActiveDraft] = useState(recommended)
  const [isEditing, setIsEditing] = useState(false)
  const [editedMessage, setEditedMessage] = useState(
    recommended === 'B' ? (data.message_draft_b || '') : (data.message_draft || '')
  )

  const draftA = data.message_draft || ''
  const draftB = data.message_draft_b || ''
  const hasBoth = draftA && draftB

  const currentDraft = isEditing
    ? editedMessage
    : (activeDraft === 'B' ? draftB : draftA)

  const person = data.person || {}
  const initials = (person.name || '?')
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  const score = data.relevance || 0
  const scoreColor =
    score >= 8 ? 'bg-green-100 text-green-700' :
    score >= 5 ? 'bg-amber-100 text-amber-700' :
    'bg-red-100 text-red-700'
  const isHotLead = score >= 9

  function handleApprove() {
    send('APPROVE', {
      contact_id: data.contact_id,
      final_message: currentDraft,
      agent_id: data.agent_id,
      session_id: data.session_id,
      context_snapshot: data.context_snapshot || {},
    })
  }

  function handleSendEdited() {
    send('EDIT_APPROVE', {
      contact_id: data.contact_id,
      final_message: editedMessage,
      edited_message: editedMessage,
      agent_id: data.agent_id,
      session_id: data.session_id,
      context_snapshot: data.context_snapshot || {},
    })
  }

  function handleSkip() {
    send('SKIP', {
      contact_id: data.contact_id,
      agent_id: data.agent_id,
      session_id: data.session_id,
      context_snapshot: data.context_snapshot || {},
      reason: '',
    })
  }

  function switchDraft(v) {
    setActiveDraft(v)
    setIsEditing(false)
    setEditedMessage(v === 'B' ? draftB : draftA)
  }

  return (
    <div className={`border rounded-lg p-4 my-2 ${isHotLead ? 'border-yellow-400' : 'border-amber-300'} bg-amber-50`}>
      {isHotLead && (
        <div className="text-xs font-semibold text-yellow-600 mb-1 uppercase tracking-wide">
          High Priority Lead
        </div>
      )}
      <div className="text-xs font-semibold text-amber-600 uppercase tracking-wide mb-3">
        Approval Required
      </div>

      {/* Person row */}
      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 rounded-full bg-purple-600 text-white text-sm font-bold flex items-center justify-center flex-shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900 text-sm truncate">{person.name}</div>
          <div className="text-xs text-gray-500 truncate">{person.title}</div>
          {person.mutual_connections > 0 && (
            <div className="text-xs text-blue-500">{person.mutual_connections} mutual connections</div>
          )}
          {person.linkedin_url && (
            <a
              href={person.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-purple-500 hover:underline"
            >
              View profile →
            </a>
          )}
        </div>
        <div className={`text-xs font-semibold px-2 py-1 rounded-full flex-shrink-0 ${scoreColor}`}>
          {score}/10
        </div>
      </div>

      {/* Reason */}
      {data.reason && (
        <div className="text-xs text-gray-500 mb-3 italic border-l-2 border-amber-300 pl-2">
          {data.reason}
        </div>
      )}

      {/* Draft tabs */}
      {hasBoth && !isEditing && (
        <div className="flex gap-1 mb-2">
          <button
            onClick={() => switchDraft('A')}
            className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
              activeDraft === 'A'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
            }`}
          >
            Draft A {recommended === 'A' && '★'}
          </button>
          <button
            onClick={() => switchDraft('B')}
            className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
              activeDraft === 'B'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
            }`}
          >
            Draft B {recommended === 'B' && '★'}
          </button>
        </div>
      )}

      {/* Message preview / edit */}
      {!isEditing ? (
        <div
          className="bg-white border border-gray-200 rounded p-3 mb-1 text-sm text-gray-700 leading-relaxed"
          style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}
        >
          {currentDraft}
        </div>
      ) : (
        <textarea
          className="w-full border border-purple-300 rounded p-3 mb-1 text-sm text-gray-700 resize-none focus:outline-none focus:ring-1 focus:ring-purple-400"
          rows={10}
          value={editedMessage}
          onChange={e => setEditedMessage(e.target.value)}
          style={{ whiteSpace: 'pre-wrap' }}
        />
      )}

      {/* Char count vs LinkedIn 300-char hard limit */}
      <div className={`text-xs mb-3 text-right font-medium ${
        (isEditing ? editedMessage : currentDraft).length > 290 ? 'text-red-500' : 'text-gray-400'
      }`}>
        {(isEditing ? editedMessage : currentDraft).length} / 300
      </div>

      {/* Actions */}
      <div className="flex gap-2 flex-wrap">
        {!isEditing ? (
          <>
            <button
              onClick={handleApprove}
              className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700"
            >
              Approve & Send
            </button>
            <button
              onClick={() => setIsEditing(true)}
              className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Edit
            </button>
            <button
              onClick={handleSkip}
              className="px-3 py-1.5 text-xs font-medium bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            >
              Skip
            </button>
          </>
        ) : (
          <>
            <button
              onClick={handleSendEdited}
              className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700"
            >
              Send Edited
            </button>
            <button
              onClick={() => setIsEditing(false)}
              className="px-3 py-1.5 text-xs font-medium bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            >
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  )
}
