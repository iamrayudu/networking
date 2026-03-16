# DEPRECATED FOR AGENT USE — replaced by backend/memory/context_object.py
# context_builder.py is kept for backward compatibility only.
# New agents must use build_initial_context() from context_object.py.
import json
from pathlib import Path
from backend.memory.database import (
    get_job, get_enrichment_by_job, get_story_by_job, get_contacts_by_job
)
from backend.memory.decision_log import get_preference_summary
from backend.config import cfg

ROOT = Path(__file__).parent.parent.parent


def build_agent_context(job_id: int, session_id: int) -> str:
    sections = []

    # === YOUR PROFILE ===
    profile_dir = ROOT / cfg['paths']['profile_dir']
    profile_text = ''
    for fname in ['master_profile.md', 'tone_guide.md']:
        fpath = profile_dir / fname
        if fpath.exists():
            profile_text += f'\n\n--- {fname} ---\n{fpath.read_text()}'
        else:
            profile_text += f'\n\n--- {fname} ---\nProfile not yet written. Ask user to create {fpath}'
    sections.append(f'=== YOUR PROFILE ==={profile_text}')

    # === ROLE CONTEXT ===
    job = get_job(job_id) or {}
    enrichment = get_enrichment_by_job(job_id) or {}
    role_lines = [
        f'Company: {job.get("company", "Unknown")}',
        f'Role: {job.get("role_title", "Unknown")}',
        f'Job URL: {job.get("job_url", "")}',
        f'Location: {job.get("location", "")}',
        f'Notes: {job.get("notes", "")}',
    ]
    if enrichment:
        role_lines += [
            '',
            f'Company Summary: {enrichment.get("company_summary", "")}',
            f'Team Info: {enrichment.get("team_info", "")}',
            f'Role Signals: {enrichment.get("role_signals", "")}',
            f'Culture Signals: {enrichment.get("culture_signals", "")}',
        ]
    sections.append('=== ROLE CONTEXT ===\n' + '\n'.join(role_lines))

    # === YOUR STORY FOR THIS ROLE ===
    story = get_story_by_job(job_id)
    if story and story.get('story_file_path'):
        story_path = ROOT / story['story_file_path']
        if story_path.exists():
            story_text = story_path.read_text()
        else:
            story_text = f'Story file missing at {story_path}'
    else:
        story_text = 'Story not yet generated for this role.'
    sections.append(f'=== YOUR STORY FOR THIS ROLE ===\n{story_text}')

    # === LEARNED PREFERENCES ===
    preferences = get_preference_summary(job_id)
    sections.append(f'=== LEARNED PREFERENCES ===\n{preferences}')

    # === PRIOR CONTACTS AT THIS COMPANY ===
    contacts = get_contacts_by_job(job_id)
    if contacts:
        contact_lines = [
            f'Already contacted: {c["full_name"]} ({c["title"]}) - status: {c["status"]}'
            for c in contacts
        ]
        prior_text = '\n'.join(contact_lines)
    else:
        prior_text = 'No prior contacts at this company.'
    sections.append(f'=== PRIOR CONTACTS AT THIS COMPANY ===\n{prior_text}')

    return '\n\n'.join(sections)
