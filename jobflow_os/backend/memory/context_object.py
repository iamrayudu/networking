import json
import logging
import datetime
from pathlib import Path
from typing import Optional
from backend.memory.database import (
    get_job, get_enrichment_by_job, get_story_by_job,
    get_contacts_by_job, save_checkpoint, get_latest_checkpoint
)
from backend.memory.decision_log import get_preference_summary
from backend.config import cfg

ROOT = Path(__file__).parent.parent.parent
logger = logging.getLogger(__name__)


def build_initial_context(job_id: int, session_id: int) -> dict:
    """
    Builds the context object ONCE at agent startup.
    Returns a dict with 5 top-level keys: permanent, session, current_person, current_score, observations.
    Raises FileNotFoundError if master_profile.md not found.
    Raises ValueError if no enrichment found for this job_id.
    """
    # Load profile files
    profile_dir = ROOT / cfg['paths']['profile_dir']
    profile_path = profile_dir / 'master_profile.md'
    tone_path = profile_dir / 'tone_guide.md'

    if not profile_path.exists():
        raise FileNotFoundError(
            "master_profile.md not found. Create profile/master_profile.md before running agents."
        )

    profile_text = profile_path.read_text()
    tone_text = tone_path.read_text() if tone_path.exists() else ''

    # Load role data
    role = get_job(job_id)
    if not role:
        raise ValueError(f"Job {job_id} not found in database.")

    enrichment = get_enrichment_by_job(job_id)
    if not enrichment:
        raise ValueError(
            f"No enrichment found for job_id {job_id}. Run enrichment agent first."
        )

    # Load story if available
    story_text = ''
    story_row = get_story_by_job(job_id)
    if story_row and story_row.get('story_file_path'):
        story_path = ROOT / story_row['story_file_path']
        if story_path.exists():
            story_text = story_path.read_text()

    # Load preferences
    preferences = get_preference_summary()

    # Load prior contacts — only SENT ones are true duplicates.
    # Contacts with status FOUND/PENDING/FAILED from previous failed runs
    # should be retried, not skipped.
    prior_contacts_list = get_contacts_by_job(job_id)
    prior_contacts_set = set(
        c['linkedin_url'] for c in prior_contacts_list
        if c.get('linkedin_url') and c.get('status') == 'SENT'
    )

    return {
        'permanent': {
            'profile': profile_text,
            'tone_guide': tone_text,
            'role': dict(role),
            'enrichment': dict(enrichment),
            'story': story_text,
            'preferences': preferences,
            'prior_contacts': prior_contacts_set,
        },
        'session': {
            'session_id': session_id,
            'agent_id': '',
            'standing_instructions': '',
            'candidates_found': [],
            'actions_taken': [],
        },
        'current_person': {
            'name': None,
            'title': None,
            'linkedin_url': None,
            'headline': None,
            'summary': None,
            'current_role_duration': None,
            'past_roles': [],
            'mutual_connections': 0,
            'connection_degree': None,
            'recent_activity': None,
            'skills_visible': [],
        },
        'current_score': {
            'score': None,
            'reason': None,
            'fit_angle': None,
            'hook_source': None,
        },
        'observations': [],
    }


def reset_for_next_person(ctx: dict) -> dict:
    """Resets current_person, current_score, and observations to defaults."""
    ctx['current_person'] = {
        'name': None,
        'title': None,
        'linkedin_url': None,
        'headline': None,
        'summary': None,
        'current_role_duration': None,
        'past_roles': [],
        'mutual_connections': 0,
        'connection_degree': None,
        'recent_activity': None,
        'skills_visible': [],
    }
    ctx['current_score'] = {
        'score': None,
        'reason': None,
        'fit_angle': None,
        'hook_source': None,
    }
    ctx['observations'] = []
    return ctx


def _ctx_to_json(ctx: dict) -> str:
    """Serialize ctx to JSON, converting sets to lists."""
    def default_serializer(obj):
        if isinstance(obj, set):
            return list(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    return json.dumps(ctx, default=default_serializer)


def _ctx_from_json(json_str: str) -> dict:
    """Deserialize ctx from JSON, converting prior_contacts list back to set."""
    ctx = json.loads(json_str)
    if 'permanent' in ctx and 'prior_contacts' in ctx['permanent']:
        ctx['permanent']['prior_contacts'] = set(ctx['permanent']['prior_contacts'])
    return ctx


def checkpoint(ctx: dict) -> None:
    """Writes ctx to SQLite. Never raises — checkpoint failure must not crash agent."""
    try:
        agent_id = ctx.get('session', {}).get('agent_id', 'unknown')
        job_id = ctx.get('permanent', {}).get('role', {}).get('id', 0)
        session_id = ctx.get('session', {}).get('session_id', 0)
        actions = ctx.get('session', {}).get('actions_taken', [])
        tool_step = actions[-1].get('step', 'unknown') if actions else 'initial'
        ctx_json = _ctx_to_json(ctx)
        save_checkpoint(agent_id, job_id, session_id, ctx_json, tool_step)
    except Exception as e:
        logger.warning(f"Checkpoint write failed (non-fatal): {e}")


def restore_checkpoint(agent_id: str, job_id: int, session_id: int) -> Optional[dict]:
    """Returns restored context dict or None if no checkpoint found."""
    try:
        ctx_json = get_latest_checkpoint(agent_id, job_id, session_id)
        if ctx_json:
            return _ctx_from_json(ctx_json)
    except Exception as e:
        logger.warning(f"Checkpoint restore failed: {e}")
    return None


def is_duplicate(linkedin_url: str, ctx: dict) -> bool:
    """Returns True if linkedin_url was already contacted or found this session."""
    prior = ctx.get('permanent', {}).get('prior_contacts', set())
    if linkedin_url in prior:
        return True
    candidates = ctx.get('session', {}).get('candidates_found', [])
    seen_urls = [c.get('linkedin_url') for c in candidates if isinstance(c, dict)]
    return linkedin_url in seen_urls


def mark_contacted(linkedin_url: str, ctx: dict) -> dict:
    """Adds linkedin_url to prior_contacts set and actions_taken list."""
    ctx['permanent']['prior_contacts'].add(linkedin_url)
    ctx['session']['actions_taken'].append({
        'step': 'sent',
        'person': linkedin_url,
        'timestamp': datetime.datetime.utcnow().isoformat(),
    })
    return ctx
