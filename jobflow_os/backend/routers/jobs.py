import threading
from fastapi import APIRouter, HTTPException
from backend.phases.phase1_input import load_jobs_from_excel
from backend.memory.database import get_all_jobs, get_job, update_job_status, get_enrichment_by_job

router = APIRouter(prefix='/api/jobs', tags=['jobs'])

# Track in-progress enrichment jobs so UI can poll
_enrich_status: dict = {}  # job_id -> "running" | "done" | "failed: ..."


@router.post('/load')
def load_jobs():
    return load_jobs_from_excel()


@router.get('/')
def list_jobs():
    return get_all_jobs()


@router.get('/{job_id}')
def get_job_detail(job_id: int):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return job


@router.get('/{job_id}/enrichment')
def get_job_enrichment(job_id: int):
    """Returns the enrichment data for a job, or null if not enriched yet."""
    import json
    from pathlib import Path
    row = get_enrichment_by_job(job_id)
    if not row:
        return None
    result = dict(row)
    # Parse JSON-encoded list fields
    for field in ('role_signals', 'culture_signals'):
        if isinstance(result.get(field), str):
            try:
                result[field] = json.loads(result[field])
            except Exception:
                result[field] = []
    # Load full enrichment from JSON file if available
    raw_path = result.get('raw_json_path')
    if raw_path and Path(raw_path).exists():
        try:
            full = json.loads(Path(raw_path).read_text())
            result['fit_indicators'] = full.get('fit_indicators', [])
            result['contact_targets'] = full.get('contact_targets', [])
            result['tech_stack'] = full.get('tech_stack', [])
            result['enrichment_confidence'] = full.get('enrichment_confidence', 'UNKNOWN')
            result['team_info'] = full.get('team_info', result.get('team_info', ''))
        except Exception:
            pass
    return result


@router.post('/{job_id}/enrich')
def enrich_job_endpoint(job_id: int, force: bool = False):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')

    if _enrich_status.get(job_id) == 'running':
        return {'status': 'already_running', 'job_id': job_id}

    # Already enriched and not forcing — skip immediately
    if not force and job.get('status') == 'ENRICHED' and get_enrichment_by_job(job_id):
        _enrich_status[job_id] = 'done'
        return {'status': 'already_enriched', 'job_id': job_id}

    def _run():
        _enrich_status[job_id] = 'running'
        try:
            from backend.agents.enrichment_agent import enrich_job
            enrich_job(job_id, force=force)
            _enrich_status[job_id] = 'done'
        except Exception as e:
            _enrich_status[job_id] = f'failed: {e}'
            update_job_status(job_id, 'ENRICHMENT_FAILED')

    threading.Thread(target=_run, daemon=True).start()
    _enrich_status[job_id] = 'running'
    return {'status': 'started', 'job_id': job_id}


@router.get('/{job_id}/enrich-status')
def enrich_status(job_id: int):
    return {'job_id': job_id, 'status': _enrich_status.get(job_id, 'idle')}


@router.post('/enrich-all')
def enrich_all_endpoint():
    jobs = [j for j in get_all_jobs() if j['status'] == 'PENDING']
    if not jobs:
        return {'status': 'nothing_to_enrich', 'job_ids': [], 'count': 0}

    started = [j['id'] for j in jobs]
    # Mark all as running NOW so the UI immediately shows "enriching..."
    for jid in started:
        _enrich_status[jid] = 'running'

    def _run_all():
        from backend.agents.enrichment_agent import enrich_job
        for job in jobs:
            jid = job['id']
            try:
                enrich_job(jid)
                _enrich_status[jid] = 'done'
            except Exception as e:
                _enrich_status[jid] = f'failed: {e}'
                update_job_status(jid, 'ENRICHMENT_FAILED')

    threading.Thread(target=_run_all, daemon=True).start()
    return {'status': 'started', 'job_ids': started, 'count': len(started)}
