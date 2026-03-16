from fastapi import APIRouter
from backend.memory.database import get_recent_decisions, get_preferences, get_all_jobs, get_contacts_by_job
from backend.memory.vector_store import search

router = APIRouter(prefix='/api/memory', tags=['memory'])


@router.post('/search')
async def memory_search(body: dict):
    results = search('jobflow_decisions', body['query'])
    return {'results': results}


@router.get('/decisions')
async def get_decisions(limit: int = 20):
    return get_recent_decisions(limit)


@router.get('/preferences')
async def get_prefs():
    return get_preferences()


@router.get('/contacts')
async def all_contacts():
    jobs = get_all_jobs()
    all_c = []
    for job in jobs:
        contacts = get_contacts_by_job(job['id'])
        for c in contacts:
            c['company'] = job['company']
            c['role'] = job['role_title']
            all_c.append(c)
    return all_c
