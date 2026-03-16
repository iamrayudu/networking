from backend.core.claude_client import ask_json
from backend.memory.database import get_decisions_by_session, upsert_preference, end_session
from backend.websocket_manager import ws_manager

UPDATE_SYSTEM = """Analyze job networking session decisions to extract preference rules.
Given a list of decisions and their inferred reasons, identify clear durable patterns.
Return JSON array:
[
  {"category": "CONTACT_TARGETING", "rule": "prefers Senior ICs over recruiters", "confidence": 0.9, "evidence_count": 4},
  {"category": "TONE", "rule": "prefers direct messages under 60 words", "confidence": 0.8, "evidence_count": 3}
]
Categories: CONTACT_TARGETING | TONE | THRESHOLD | TIMING | COMPANY_TYPE
Return only JSON array. Empty array if no clear patterns."""


def run_preference_update(session_id: int):
    decisions = get_decisions_by_session(session_id)
    if not decisions:
        end_session(session_id, {})
        return

    summary = 'SESSION DECISIONS:\n' + '\n'.join([
        f"- {d['action_type']}: {d['inferred_preference']}"
        for d in decisions if d.get('inferred_preference')
    ])

    try:
        preferences = ask_json(summary, system=UPDATE_SYSTEM)
    except Exception:
        preferences = []

    updated = 0
    if isinstance(preferences, list):
        for pref in preferences:
            upsert_preference(
                pref['category'], pref['rule'],
                pref.get('evidence_count', 1), pref.get('confidence', 0.5)
            )
            updated += 1

    stats = {
        'contacts_found': sum(1 for d in decisions if d['action_type'] in ('APPROVE', 'EDIT_APPROVE', 'SKIP')),
        'messages_sent': sum(1 for d in decisions if d['action_type'] in ('APPROVE', 'EDIT_APPROVE')),
        'preferences_updated': updated,
    }
    end_session(session_id, stats)

    try:
        ws_manager.send_sync('frontend', 'SESSION_COMPLETE', {
            'agent_id': 'system',
            'preferences_updated': updated,
            'summary': f'Session complete. {updated} preferences learned/updated.',
        })
    except Exception:
        pass
