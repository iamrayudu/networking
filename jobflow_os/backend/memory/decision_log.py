import json
import uuid
import datetime
from backend.memory.database import (
    insert_decision, update_decision_chroma_id,
    get_recent_decisions, get_preferences
)
from backend.memory.vector_store import embed
from backend.core.claude_client import ask_json
from backend.skills.skill_loader import inject_skill_as_system


def record_decision(session_id: int, action_type: str, context_snapshot: dict, your_action: str) -> int:
    # 1. Build prompt for Claude
    prompt = f"Action: {action_type}\nContext: {json.dumps(context_snapshot)}\nUser did: {your_action}"

    # 2. Call Claude to infer why using micro-skill
    try:
        system = inject_skill_as_system("preference_infer")
        inference = ask_json(prompt, system=system)
        inferred_why = inference.get('inferred_why', '')
        inferred_preference = inference.get('inferred_preference', '')
        confidence = inference.get('confidence', 3)
    except Exception:
        inferred_why = ''
        inferred_preference = ''
        confidence = 3

    # 3. Insert into decision_log
    now = datetime.datetime.utcnow().isoformat()
    decision_id = insert_decision({
        'session_id': session_id,
        'action_type': action_type,
        'context_snapshot': json.dumps(context_snapshot),
        'your_action': your_action,
        'inferred_why': inferred_why,
        'inferred_preference': inferred_preference,
        'confidence': confidence,
        'timestamp': now,
    })

    # 4. Generate chroma_id and embed
    chroma_id = str(uuid.uuid4())
    text = f"{action_type}: {your_action}. Why: {inferred_why}. Preference: {inferred_preference}"
    embed('jobflow_decisions', chroma_id, text, {
        'session_id': session_id,
        'action_type': action_type,
        'job_id': context_snapshot.get('job_id', 0),
    })

    # 5. Update row with chroma_id
    update_decision_chroma_id(decision_id, chroma_id)

    return decision_id


def get_preference_summary(job_id: int = None) -> str:
    prefs = get_preferences()
    decisions = get_recent_decisions(limit=20)

    lines = ['LEARNED PREFERENCES:']
    if prefs:
        lines += [f"- {p['rule']} (confidence: {p['confidence']:.1f})" for p in prefs]
    else:
        lines.append('- No preferences learned yet.')

    lines += ['', 'RECENT DECISION PATTERNS:']
    patterns = [d['inferred_preference'] for d in decisions if d.get('inferred_preference')]
    if patterns:
        lines += [f"- {p}" for p in patterns]
    else:
        lines.append('- No recent decisions recorded.')

    return '\n'.join(lines)
