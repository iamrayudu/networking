import json
import re
import datetime
from pathlib import Path
from backend.core.claude_client import ask
from backend.memory.database import (
    get_job, get_enrichment_by_job, get_all_jobs, insert_story, update_job_status
)
from backend.memory.decision_log import get_preference_summary
from backend.memory.vector_store import embed
from backend.memory.output_schemas import validate_step
from backend.skills.skill_loader import inject_skill_with_voice
from backend.config import cfg

ROOT = Path(__file__).parent.parent.parent


def load_profile() -> str:
    profile_dir = ROOT / cfg['paths']['profile_dir']
    text = ''
    for fname in ['master_profile.md', 'tone_guide.md']:
        fpath = profile_dir / fname
        if fpath.exists():
            text += f'\n\n=== {fname} ===\n' + fpath.read_text()
        else:
            text += f'\n\n=== {fname} ===\nNot found. Create {fpath} with your background.'
    return text


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[^\w\-]', '_', name)[:50]


def _parse_section(text: str, header: str) -> str:
    pattern = rf'{re.escape(header)}[:\s]*(.*?)(?=\n[A-Z_]+:|$)'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ''


def generate_story(job_id: int) -> dict:
    job = get_job(job_id)
    if not job:
        raise ValueError(f'Job {job_id} not found')

    enrichment = get_enrichment_by_job(job_id) or {}
    profile = load_profile()
    preferences = get_preference_summary(job_id)

    # Build a minimal ctx for voice anchor (story agent doesn't use full context object)
    minimal_ctx = {
        'permanent': {
            'tone_guide': '',
            'preferences': preferences,
        },
        'current_score': {
            'fit_angle': None,
        },
        'observations': [],
    }
    # Try to load tone_guide for voice anchor
    tone_path = ROOT / cfg['paths']['profile_dir'] / 'tone_guide.md'
    if tone_path.exists():
        minimal_ctx['permanent']['tone_guide'] = tone_path.read_text()

    prompt = (
        f"CANDIDATE PROFILE:\n{profile}\n\n"
        f"ROLE: {job['company']} - {job['role_title']}\n"
        f"ENRICHMENT:\n{json.dumps(enrichment)}\n\n"
        f"LEARNED PREFERENCES:\n{preferences}"
    )

    system = inject_skill_with_voice("story_write", minimal_ctx)
    response = ask(prompt, system=system, max_tokens=cfg['claude']['story_max_tokens'])

    # Save story to disk
    stories_dir = ROOT / cfg['paths']['stories']
    stories_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_sanitize_filename(job['company'])}_{_sanitize_filename(job['role_title'])}.md"
    story_path = stories_dir / filename
    story_path.write_text(response)

    # Parse sections
    now = datetime.datetime.utcnow().isoformat()

    # Parse key_strengths and talking_points as lists
    ks_text = _parse_section(response, 'KEY_STRENGTHS')
    tp_text = _parse_section(response, 'TALKING_POINTS')
    ks_list = [line.strip().lstrip('- ') for line in ks_text.split('\n') if line.strip().startswith('-')]
    tp_list = [line.strip().lstrip('- ') for line in tp_text.split('\n') if line.strip().startswith('-')]

    parsed = {
        'headline': _parse_section(response, 'HEADLINE'),
        'key_strengths': ks_list or ks_text,
        'talking_points': tp_list or tp_text,
        'gap_framing': _parse_section(response, 'GAP_FRAMING') or "No significant gaps identified.",
        'outreach_tone': _parse_section(response, 'OUTREACH_TONE'),
    }

    # Validate story output
    parsed = validate_step(parsed, "story")

    story_data = {
        'job_id': job_id,
        'story_file_path': str(story_path.relative_to(ROOT)),
        'headline': parsed['headline'],
        'key_strengths': json.dumps(parsed['key_strengths']) if isinstance(parsed['key_strengths'], list) else parsed['key_strengths'],
        'talking_points': json.dumps(parsed['talking_points']) if isinstance(parsed['talking_points'], list) else parsed['talking_points'],
        'gaps_to_address': parsed['gap_framing'],
        'generated_at': now,
        'last_edited_at': now,
    }

    insert_story(story_data)

    # Embed into ChromaDB
    embed('jobflow_stories', f'story_{job_id}', response, {
        'job_id': job_id,
        'company': job['company'],
        'role': job['role_title'],
    })

    update_job_status(job_id, 'STORY_READY')
    return story_data


def generate_all_stories() -> dict:
    jobs = [j for j in get_all_jobs() if j['status'] == 'ENRICHED']
    generated = 0
    failed = 0
    for job in jobs:
        try:
            generate_story(job['id'])
            generated += 1
        except Exception as e:
            print(f"Failed story for {job['company']}: {e}")
            failed += 1
    return {'generated': generated, 'failed': failed}
