from fastapi import APIRouter
from pydantic import BaseModel
from backend.memory.database import update_contact_status, insert_approval
from backend.memory.decision_log import record_decision

router = APIRouter(prefix='/api/approvals', tags=['approvals'])


class ApproveRequest(BaseModel):
    contact_id: int
    final_message: str
    session_id: int
    context_snapshot: dict
    agent_id: str


class SkipRequest(BaseModel):
    contact_id: int
    reason: str = ''
    session_id: int
    context_snapshot: dict
    agent_id: str


@router.post('/approve')
async def approve(req: ApproveRequest):
    update_contact_status(req.contact_id, 'SENT')
    insert_approval({
        'contact_id': req.contact_id,
        'action': 'APPROVE',
        'final_message': req.final_message,
        'edited': False,
    })
    record_decision(req.session_id, 'APPROVE', req.context_snapshot, req.final_message)
    # Import here to avoid circular import at module load time
    from backend.workers.agent_pool import pool
    pool.notify_agent(req.agent_id, 'approve', {
        'final_message': req.final_message, 'contact_id': req.contact_id
    })
    return {'status': 'approved', 'contact_id': req.contact_id}


@router.post('/edit_approve')
async def edit_approve(req: ApproveRequest):
    update_contact_status(req.contact_id, 'SENT')
    insert_approval({
        'contact_id': req.contact_id,
        'action': 'EDIT_APPROVE',
        'final_message': req.final_message,
        'edited': True,
    })
    record_decision(req.session_id, 'EDIT_APPROVE', req.context_snapshot, req.final_message)
    from backend.workers.agent_pool import pool
    pool.notify_agent(req.agent_id, 'edit', {
        'final_message': req.final_message, 'contact_id': req.contact_id
    })
    return {'status': 'approved', 'contact_id': req.contact_id}


@router.post('/skip')
async def skip(req: SkipRequest):
    update_contact_status(req.contact_id, 'SKIPPED')
    insert_approval({
        'contact_id': req.contact_id,
        'action': 'SKIP',
        'final_message': '',
    })
    record_decision(req.session_id, 'SKIP', req.context_snapshot, f'Skipped. {req.reason}')
    from backend.workers.agent_pool import pool
    pool.notify_agent(req.agent_id, 'skip', {'contact_id': req.contact_id})
    return {'status': 'skipped', 'contact_id': req.contact_id}
