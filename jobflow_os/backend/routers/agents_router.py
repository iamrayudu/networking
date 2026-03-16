from fastapi import APIRouter

router = APIRouter(prefix='/api/agents', tags=['agents'])


@router.post('/start')
async def start(body: dict):
    from backend.workers.agent_pool import pool
    session_id = pool.start_session(body['job_ids'], body.get('standing_instructions', ''))
    return {'session_id': session_id, 'agents_started': len(body['job_ids'])}


@router.post('/{agent_id}/pause')
async def pause(agent_id: str):
    from backend.workers.agent_pool import pool
    pool.pause_agent(agent_id)
    return {'status': 'paused'}


@router.post('/{agent_id}/resume')
async def resume(agent_id: str):
    from backend.workers.agent_pool import pool
    pool.resume_agent(agent_id)
    return {'status': 'resumed'}


@router.post('/{agent_id}/stop')
async def stop(agent_id: str):
    from backend.workers.agent_pool import pool
    pool.stop_agent(agent_id)
    return {'status': 'stopped'}


@router.get('/status')
async def status():
    from backend.workers.agent_pool import pool
    return pool.get_all_status()


@router.get('/{agent_id}/log')
async def agent_log(agent_id: str, limit: int = 10):
    from backend.memory.database import get_conn
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM agent_log WHERE agent_id = ? ORDER BY timestamp DESC LIMIT ?',
        (agent_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
