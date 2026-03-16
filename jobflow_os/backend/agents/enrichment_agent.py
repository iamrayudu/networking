import json
import logging
import time
import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from backend.core.claude_client import ask_json
from backend.memory.database import get_job, get_all_jobs, insert_enrichment, update_job_status, log_agent_action
from backend.memory.output_schemas import validate_step
from backend.skills.skill_loader import inject_skill_as_system
from backend.agents.failure_handler import with_retry
from backend.config import cfg

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent

SEARCH_TEMPLATES = [
    '{company} company overview engineering team culture',
    '{company} {role} job requirements skills experience',
    '{company} recent news funding product 2024 2025',
    '{company} linkedin employees team size',
]


def fetch_page_text(url: str, max_chars: int = 3000) -> str:
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        response = requests.get(url, timeout=8, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        return text[:max_chars]
    except Exception:
        return ''


def search_and_fetch(query: str, n_results: int = 3) -> str:
    texts = []
    try:
        results = DDGS().text(query, max_results=n_results)
        for result in results:
            href = result.get('href', '')
            if href:
                text = fetch_page_text(href)
                if text:
                    texts.append(text)
                time.sleep(cfg['enrichment']['search_delay_seconds'])
    except Exception:
        pass
    return '\n\n'.join(texts)


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[^\w\-]', '_', name)[:50]


def enrich_job(job_id: int, force: bool = False) -> dict:
    job = get_job(job_id)
    if not job:
        raise ValueError(f'Job {job_id} not found')

    company = job['company']
    role = job['role_title']

    # Guard: already enriched — return cached data, skip web search + Claude call
    if not force and job.get('status') == 'ENRICHED':
        from backend.memory.database import get_enrichment_by_job
        existing = get_enrichment_by_job(job_id)
        if existing and existing.get('raw_json_path'):
            cached_path = Path(existing['raw_json_path'])
            if cached_path.exists():
                logger.info(f'enrich_job: job {job_id} ({company}) already enriched — returning cached data')
                return json.loads(cached_path.read_text())
        # File missing but DB says enriched — fall through and re-enrich
        logger.warning(f'enrich_job: job {job_id} ({company}) status=ENRICHED but cached file missing — re-enriching')
    _log = lambda action, detail, status='SUCCESS': log_agent_action(
        'enrichment', job_id, None, action, detail, status
    )

    _log('ENRICH_START', f'{company} — {role}')
    update_job_status(job_id, 'IN_PROGRESS')

    # Run all search templates
    all_text = ''
    for template in SEARCH_TEMPLATES:
        query = template.format(company=company, role=role)
        _log('SEARCH', query)
        fetched = search_and_fetch(query)
        if fetched:
            all_text += '\n\n' + fetched
            _log('SEARCH_OK', f'{len(fetched)} chars fetched for: {query[:60]}')
        else:
            _log('SEARCH_EMPTY', f'No results for: {query[:60]}', 'SKIPPED')

    _log('CLAUDE_CALL', f'Synthesising {len(all_text)} chars of research')

    # If no text was fetched, provide a minimal placeholder so Claude call doesn't fail
    research_text = all_text.strip()[:8000] if all_text.strip() else f'Company: {company}\nRole: {role}\nNo web data was fetched — synthesise what you know about this company and role.'

    # Synthesize with Claude using micro-skill
    system = inject_skill_as_system("enrichment_synthesise")
    try:
        enrichment = ask_json(research_text, system=system)
    except ValueError as e:
        _log('CLAUDE_PARSE_ERROR', str(e)[:200], 'FAILED')
        enrichment = with_retry(
            lambda: ask_json(research_text, system=system),
            failure_type="claude_json_parse_error",
            agent=None, ctx={}
        )
        if enrichment is None:
            update_job_status(job_id, 'ENRICHMENT_FAILED')
            _log('ENRICH_FAILED', f'Claude returned unparseable data after retry', 'FAILED')
            raise ValueError(
                f"Enrichment failed for {company} — Claude returned unparseable data. "
                "Try again or skip this role."
            )
        _log('CLAUDE_RETRY_OK', 'Retry succeeded')

    # Validate enrichment output
    enrichment = validate_step(enrichment, "enrichment")
    confidence = enrichment.get('enrichment_confidence', 'UNKNOWN')
    fit_count = len(enrichment.get('fit_indicators', []))
    role_signal_count = len(enrichment.get('role_signals', []))
    _log('ENRICH_VALIDATED', f'confidence={confidence} fit_indicators={fit_count} role_signals={role_signal_count}')

    # Save raw JSON to disk
    enriched_dir = ROOT / cfg['paths']['enriched_data']
    enriched_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_sanitize_filename(company)}_{_sanitize_filename(role)}.json"
    raw_path = enriched_dir / filename
    raw_path.write_text(json.dumps(enrichment, indent=2))

    # Store in DB
    insert_enrichment({
        'job_id': job_id,
        'company_summary': enrichment.get('company_summary', ''),
        'team_info': enrichment.get('team_info', ''),
        'role_signals': json.dumps(enrichment.get('role_signals', [])),
        'culture_signals': json.dumps(enrichment.get('culture_signals', [])),
        'linkedin_company_url': enrichment.get('linkedin_company_url', ''),
        'raw_json_path': str(raw_path),
    })

    update_job_status(job_id, 'ENRICHED')
    _log('ENRICH_DONE', f'Saved to {filename}')
    return enrichment


def enrich_all_pending() -> dict:
    jobs = [j for j in get_all_jobs() if j['status'] == 'PENDING']
    enriched = 0
    failed = 0
    for job in jobs:
        try:
            enrich_job(job['id'])
            enriched += 1
        except Exception as e:
            logger.error(f"Failed to enrich {job['company']}: {e}")
            log_agent_action('enrichment', job['id'], 0, 'ENRICH_ALL_FAILED', str(e)[:300], 'FAILED')
            failed += 1
    return {'enriched': enriched, 'failed': failed}
