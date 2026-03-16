import os
from fastapi import APIRouter, Query
from backend.memory.database import get_conn

router = APIRouter(prefix='/api/logs', tags=['logs'])


@router.get('/')
def get_agent_logs(
    agent_id: str = Query(None),
    session_id: int = Query(None),
    status: str = Query(None),
    limit: int = Query(200),
):
    """
    Returns agent_log entries. Supports filtering by agent_id, session_id, status.
    status options: SUCCESS, FAILED, SKIPPED, ERROR
    """
    conn = get_conn()
    conditions = []
    params = []

    if agent_id:
        conditions.append('l.agent_id = ?')
        params.append(agent_id)
    if session_id:
        conditions.append('l.session_id = ?')
        params.append(session_id)
    if status:
        conditions.append('l.status = ?')
        params.append(status.upper())

    where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

    rows = conn.execute(f'''
        SELECT l.id, l.agent_id, l.job_id, l.session_id, l.action, l.detail,
               l.status, l.timestamp, j.company, j.role_title
        FROM agent_log l
        LEFT JOIN jobs j ON l.job_id = j.id
        {where}
        ORDER BY l.id DESC
        LIMIT ?
    ''', params + [limit]).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get('/failures')
def get_failures(
    agent_id: str = Query(None),
    session_id: int = Query(None),
    severity: str = Query(None),
    limit: int = Query(100),
):
    """
    Returns agent_failures entries.
    severity options: CRITICAL, HIGH, MEDIUM, LOW
    """
    conn = get_conn()
    conditions = []
    params = []

    if agent_id:
        conditions.append('f.agent_id = ?')
        params.append(agent_id)
    if session_id:
        conditions.append('f.session_id = ?')
        params.append(session_id)
    if severity:
        conditions.append('f.severity = ?')
        params.append(severity.upper())

    where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

    rows = conn.execute(f'''
        SELECT f.id, f.agent_id, f.job_id, f.session_id, f.failure_type,
               f.severity, f.action_taken, f.detail, f.recovered, f.timestamp,
               j.company, j.role_title
        FROM agent_failures f
        LEFT JOIN jobs j ON f.job_id = j.id
        {where}
        ORDER BY f.id DESC
        LIMIT ?
    ''', params + [limit]).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get('/sessions')
def get_sessions(limit: int = Query(20)):
    """Returns all sessions with stats."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT s.id, s.started_at, s.ended_at, s.standing_instructions,
               s.contacts_found, s.messages_sent,
               COUNT(DISTINCT l.id) as log_entries,
               COUNT(DISTINCT f.id) as failure_count
        FROM sessions s
        LEFT JOIN agent_log l ON l.session_id = s.id
        LEFT JOIN agent_failures f ON f.session_id = s.id
        GROUP BY s.id
        ORDER BY s.id DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get('/enrichment')
def get_enrichment_log(limit: int = Query(100)):
    """Returns enrichment status for all jobs."""
    conn = get_conn()
    rows = conn.execute('''
        SELECT j.id, j.company, j.role_title, j.status, j.updated_at,
               e.company_summary IS NOT NULL as has_enrichment,
               e.enriched_at,
               CASE WHEN e.raw_json_path IS NOT NULL THEN 'stored' ELSE NULL END as enrichment_file
        FROM jobs j
        LEFT JOIN enrichment e ON e.job_id = j.id
        ORDER BY j.updated_at DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get('/timeline')
def get_timeline(session_id: int = Query(None), limit: int = Query(500)):
    """
    Returns a merged timeline of all events (agent_log + agent_failures)
    sorted by timestamp, for a full picture of what happened.
    """
    conn = get_conn()
    s_filter = 'AND l.session_id = ?' if session_id else ''
    params_log = ([session_id] if session_id else []) + [limit]

    logs = conn.execute(f'''
        SELECT l.timestamp, l.agent_id, 'LOG' as event_source,
               l.action as event_type, l.detail, l.status as level,
               j.company
        FROM agent_log l
        LEFT JOIN jobs j ON l.job_id = j.id
        WHERE 1=1 {s_filter}
        ORDER BY l.id DESC LIMIT ?
    ''', params_log).fetchall()

    s_filter_f = 'AND f.session_id = ?' if session_id else ''
    params_fail = ([session_id] if session_id else []) + [limit]

    failures = conn.execute(f'''
        SELECT f.timestamp, f.agent_id, 'FAILURE' as event_source,
               f.failure_type as event_type, f.detail, f.severity as level,
               j.company
        FROM agent_failures f
        LEFT JOIN jobs j ON f.job_id = j.id
        WHERE 1=1 {s_filter_f}
        ORDER BY f.id DESC LIMIT ?
    ''', params_fail).fetchall()

    conn.close()

    merged = [dict(r) for r in logs] + [dict(r) for r in failures]
    merged.sort(key=lambda x: x['timestamp'] or '', reverse=True)
    return merged[:limit]


@router.get('/file')
def get_log_file(lines: int = Query(200)):
    """
    Returns the last N lines from logs/jobflow.log as plain text.
    Used by the Live File Log viewer in the dashboard.
    """
    log_path = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'jobflow.log')
    log_path = os.path.normpath(log_path)
    if not os.path.exists(log_path):
        return {"lines": [], "path": log_path, "exists": False}
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
        tail = [l.rstrip('\n') for l in all_lines[-lines:]]
        return {"lines": tail, "path": log_path, "exists": True, "total": len(all_lines)}
    except Exception as e:
        return {"lines": [f"Error reading log file: {e}"], "path": log_path, "exists": True}
