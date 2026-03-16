import pandas as pd
from pathlib import Path
from backend.memory.database import insert_job, get_all_jobs
from backend.config import cfg

REQUIRED_COLUMNS = ['Company', 'Role']
OPTIONAL_COLUMNS = ['Job URL', 'Location', 'Notes', 'Priority']


def parse_excel(path: str) -> list:
    df = pd.read_excel(path)

    # Check required columns
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Excel file is missing required columns: {missing}. "
            f"Required: {REQUIRED_COLUMNS}. Found: {list(df.columns)}"
        )

    jobs = []
    for _, row in df.iterrows():
        company = str(row['Company']).strip()
        role_title = str(row['Role']).strip()
        if not company or not role_title or company == 'nan' or role_title == 'nan':
            continue
        jobs.append({
            'company': company,
            'role_title': role_title,
            'job_url': str(row.get('Job URL', '') or '').strip(),
            'location': str(row.get('Location', '') or '').strip(),
            'notes': str(row.get('Notes', '') or '').strip(),
            'priority': int(row['Priority']) if 'Priority' in row and pd.notna(row.get('Priority')) else 2,
        })
    return jobs


def load_jobs_from_excel(path: str = None) -> dict:
    path = path or cfg['paths']['input_excel']

    try:
        rows = parse_excel(path)
    except Exception as e:
        return {'loaded': 0, 'skipped': 0, 'errors': [str(e)]}

    # Build set of existing company+role combos to dedup
    existing = get_all_jobs()
    existing_keys = {(j['company'].lower(), j['role_title'].lower()) for j in existing}

    loaded = 0
    skipped = 0
    errors = []

    for job in rows:
        key = (job['company'].lower(), job['role_title'].lower())
        if key in existing_keys:
            skipped += 1
            continue
        try:
            insert_job(job)
            existing_keys.add(key)
            loaded += 1
        except Exception as e:
            errors.append(f"{job['company']}/{job['role_title']}: {e}")

    return {'loaded': loaded, 'skipped': skipped, 'errors': errors}
