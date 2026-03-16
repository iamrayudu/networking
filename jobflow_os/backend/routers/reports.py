import csv
import datetime
import io
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse
from backend.memory.database import get_all_jobs, get_contacts_by_job
from backend.config import cfg

ROOT = Path(__file__).parent.parent.parent
router = APIRouter(prefix='/api/reports', tags=['reports'])


@router.post('/summary')
async def generate_summary():
    jobs = get_all_jobs()
    all_contacts = []
    for job in jobs:
        contacts = get_contacts_by_job(job['id'])
        all_contacts.extend(contacts)
    sent = [c for c in all_contacts if c['status'] == 'SENT']

    lines = [
        f"# JobFlow OS Run Summary - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Total roles: {len(jobs)}",
        f"Total contacts found: {len(all_contacts)}",
        f"Messages sent: {len(sent)}",
        '',
        '## Roles worked:',
    ]
    for job in jobs:
        lines.append(f"- {job['company']} / {job['role_title']} — status: {job['status']}")

    report_dir = ROOT / cfg['paths']['reports']
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.md"
    report_path.write_text('\n'.join(lines))
    return {'file': str(report_path), 'summary': lines}


@router.get('/contacts.csv')
async def contacts_csv():
    jobs = get_all_jobs()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Title', 'Company', 'Role', 'LinkedIn', 'Score', 'Status', 'Message', 'Contacted'])
    for job in jobs:
        for c in get_contacts_by_job(job['id']):
            writer.writerow([
                c['full_name'], c['title'], job['company'], job['role_title'],
                c['linkedin_url'], c['relevance_score'], c['status'],
                c.get('invite_message', ''), c.get('contacted_at', ''),
            ])
    report_dir = ROOT / cfg['paths']['reports']
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / 'contacts.csv'
    path.write_text(output.getvalue())
    return FileResponse(str(path), filename='contacts.csv')


@router.get('/outreach.csv')
async def outreach_csv():
    jobs = get_all_jobs()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Title', 'Company', 'Role', 'LinkedIn', 'Score', 'Status', 'Message', 'Contacted'])
    for job in jobs:
        for c in get_contacts_by_job(job['id']):
            if c['status'] in ('SENT', 'REPLIED'):
                writer.writerow([
                    c['full_name'], c['title'], job['company'], job['role_title'],
                    c['linkedin_url'], c['relevance_score'], c['status'],
                    c.get('invite_message', ''), c.get('contacted_at', ''),
                ])
    report_dir = ROOT / cfg['paths']['reports']
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / 'outreach.csv'
    path.write_text(output.getvalue())
    return FileResponse(str(path), filename='outreach.csv')
