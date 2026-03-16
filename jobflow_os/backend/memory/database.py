import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'jobflow.db'


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at DATETIME,
            ended_at DATETIME,
            standing_instructions TEXT,
            jobs_count INTEGER DEFAULT 0,
            contacts_found INTEGER DEFAULT 0,
            messages_sent INTEGER DEFAULT 0,
            preferences_updated INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            role_title TEXT,
            job_url TEXT,
            location TEXT,
            notes TEXT,
            priority INTEGER DEFAULT 2,
            status TEXT DEFAULT 'PENDING',
            created_at DATETIME,
            updated_at DATETIME
        );

        CREATE TABLE IF NOT EXISTS enrichment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER REFERENCES jobs(id),
            company_summary TEXT,
            team_info TEXT,
            role_signals TEXT,
            culture_signals TEXT,
            linkedin_company_url TEXT,
            raw_json_path TEXT,
            enriched_at DATETIME
        );

        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER REFERENCES jobs(id),
            story_file_path TEXT,
            headline TEXT,
            key_strengths TEXT,
            talking_points TEXT,
            gaps_to_address TEXT,
            generated_at DATETIME,
            last_edited_at DATETIME
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER REFERENCES jobs(id),
            session_id INTEGER REFERENCES sessions(id),
            full_name TEXT,
            linkedin_url TEXT,
            title TEXT,
            relevance_score INTEGER,
            relevance_reason TEXT,
            invite_message TEXT,
            email_draft TEXT,
            status TEXT DEFAULT 'FOUND',
            agent_id TEXT,
            chroma_id TEXT,
            contacted_at DATETIME
        );

        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER REFERENCES contacts(id),
            action TEXT,
            original_message TEXT,
            final_message TEXT,
            edited BOOLEAN DEFAULT 0,
            timestamp DATETIME
        );

        CREATE TABLE IF NOT EXISTS agent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT,
            job_id INTEGER REFERENCES jobs(id),
            session_id INTEGER REFERENCES sessions(id),
            action TEXT,
            detail TEXT,
            status TEXT,
            timestamp DATETIME
        );

        CREATE TABLE IF NOT EXISTS decision_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER REFERENCES sessions(id),
            action_type TEXT,
            context_snapshot TEXT,
            your_action TEXT,
            inferred_why TEXT,
            inferred_preference TEXT,
            confidence INTEGER,
            chroma_id TEXT,
            timestamp DATETIME
        );

        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            rule TEXT,
            evidence_count INTEGER DEFAULT 1,
            confidence REAL DEFAULT 0.5,
            first_observed DATETIME,
            last_updated DATETIME,
            active BOOLEAN DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS agent_checkpoints (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id   TEXT NOT NULL,
            job_id     INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            ctx_json   TEXT NOT NULL,
            tool_step  TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_checkpoint_lookup
            ON agent_checkpoints(agent_id, job_id, session_id);

        CREATE TABLE IF NOT EXISTS agent_failures (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id     TEXT,
            job_id       INTEGER,
            session_id   INTEGER,
            failure_type TEXT NOT NULL,
            severity     TEXT NOT NULL,
            action_taken TEXT NOT NULL,
            detail       TEXT,
            recovered    BOOLEAN DEFAULT 0,
            timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    conn.commit()
    conn.close()
    print("Database initialized. All 11 tables created.")


# ── Jobs ──────────────────────────────────────────────────────────────────────

def insert_job(data: dict) -> int:
    now = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO jobs (company, role_title, job_url, location, notes, priority, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get('company'), data.get('role_title'), data.get('job_url', ''),
         data.get('location', ''), data.get('notes', ''), data.get('priority', 2),
         data.get('status', 'PENDING'), now, now)
    )
    job_id = c.lastrowid
    conn.commit()
    conn.close()
    return job_id


def get_job(id: int) -> dict:
    conn = get_conn()
    row = conn.execute('SELECT * FROM jobs WHERE id = ?', (id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_jobs() -> list:
    conn = get_conn()
    rows = conn.execute('SELECT * FROM jobs ORDER BY priority, created_at').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_job_status(id: int, status: str):
    now = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute('UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?', (status, now, id))
    conn.commit()
    conn.close()


# ── Enrichment ────────────────────────────────────────────────────────────────

def insert_enrichment(data: dict) -> int:
    """Upserts enrichment for a job — deletes any existing row first, preventing duplicates."""
    now = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM enrichment WHERE job_id = ?', (data.get('job_id'),))
    c.execute(
        '''INSERT INTO enrichment (job_id, company_summary, team_info, role_signals,
           culture_signals, linkedin_company_url, raw_json_path, enriched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get('job_id'), data.get('company_summary'), data.get('team_info'),
         data.get('role_signals'), data.get('culture_signals'),
         data.get('linkedin_company_url'), data.get('raw_json_path'),
         data.get('enriched_at', now))
    )
    eid = c.lastrowid
    conn.commit()
    conn.close()
    return eid


def get_enrichment_by_job(job_id: int) -> dict:
    conn = get_conn()
    row = conn.execute('SELECT * FROM enrichment WHERE job_id = ? ORDER BY id DESC LIMIT 1', (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Stories ───────────────────────────────────────────────────────────────────

def insert_story(data: dict) -> int:
    now = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO stories (job_id, story_file_path, headline, key_strengths,
           talking_points, gaps_to_address, generated_at, last_edited_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get('job_id'), data.get('story_file_path'), data.get('headline'),
         data.get('key_strengths'), data.get('talking_points'),
         data.get('gaps_to_address'), data.get('generated_at', now),
         data.get('last_edited_at', now))
    )
    sid = c.lastrowid
    conn.commit()
    conn.close()
    return sid


def get_story_by_job(job_id: int) -> dict:
    conn = get_conn()
    row = conn.execute('SELECT * FROM stories WHERE job_id = ? ORDER BY id DESC LIMIT 1', (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Contacts ──────────────────────────────────────────────────────────────────

def insert_contact(data: dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    # Database-level duplicate guard for parallel agent safety
    existing = c.execute(
        'SELECT id FROM contacts WHERE linkedin_url = ? AND job_id = ?',
        (data.get('linkedin_url', ''), data.get('job_id', 0))
    ).fetchone()
    if existing:
        conn.close()
        return existing['id']
    c.execute(
        '''INSERT INTO contacts (job_id, session_id, full_name, linkedin_url, title,
           relevance_score, relevance_reason, invite_message, email_draft, status,
           agent_id, chroma_id, contacted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get('job_id'), data.get('session_id'), data.get('full_name'),
         data.get('linkedin_url'), data.get('title'), data.get('relevance_score'),
         data.get('relevance_reason'), data.get('invite_message'), data.get('email_draft'),
         data.get('status', 'FOUND'), data.get('agent_id'), data.get('chroma_id'),
         data.get('contacted_at'))
    )
    cid = c.lastrowid
    conn.commit()
    conn.close()
    return cid


def get_contacts_by_job(job_id: int) -> list:
    conn = get_conn()
    rows = conn.execute('SELECT * FROM contacts WHERE job_id = ? ORDER BY relevance_score DESC', (job_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_contact_status(id: int, status: str):
    now = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute('UPDATE contacts SET status = ?, contacted_at = ? WHERE id = ?', (status, now, id))
    conn.commit()
    conn.close()


# ── Approvals ─────────────────────────────────────────────────────────────────

def insert_approval(data: dict) -> int:
    now = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO approvals (contact_id, action, original_message, final_message, edited, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (data.get('contact_id'), data.get('action'), data.get('original_message', ''),
         data.get('final_message', ''), data.get('edited', False),
         data.get('timestamp', now))
    )
    aid = c.lastrowid
    conn.commit()
    conn.close()
    return aid


# ── Agent log ─────────────────────────────────────────────────────────────────

def log_agent_action(agent_id, job_id, session_id, action, detail, status='SUCCESS'):
    now = datetime.datetime.utcnow().isoformat()
    # Treat 0 or invalid session_id as NULL to avoid FK constraint failures
    safe_session_id = session_id if session_id and session_id > 0 else None
    try:
        conn = get_conn()
        conn.execute(
            '''INSERT INTO agent_log (agent_id, job_id, session_id, action, detail, status, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (agent_id, job_id, safe_session_id, action, detail, status, now)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # never crash the caller over a log write


# ── Decision log ──────────────────────────────────────────────────────────────

def insert_decision(data: dict) -> int:
    now = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO decision_log (session_id, action_type, context_snapshot, your_action,
           inferred_why, inferred_preference, confidence, chroma_id, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get('session_id'), data.get('action_type'), data.get('context_snapshot'),
         data.get('your_action'), data.get('inferred_why'), data.get('inferred_preference'),
         data.get('confidence'), data.get('chroma_id'), data.get('timestamp', now))
    )
    did = c.lastrowid
    conn.commit()
    conn.close()
    return did


def update_decision_chroma_id(decision_id: int, chroma_id: str):
    conn = get_conn()
    conn.execute('UPDATE decision_log SET chroma_id = ? WHERE id = ?', (chroma_id, decision_id))
    conn.commit()
    conn.close()


def get_decisions_by_session(session_id: int) -> list:
    conn = get_conn()
    rows = conn.execute('SELECT * FROM decision_log WHERE session_id = ? ORDER BY timestamp', (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_decisions(limit: int = 50) -> list:
    conn = get_conn()
    rows = conn.execute('SELECT * FROM decision_log ORDER BY timestamp DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Preferences ───────────────────────────────────────────────────────────────

def upsert_preference(category: str, rule: str, evidence_count: int, confidence: float):
    now = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    existing = conn.execute(
        'SELECT id FROM preferences WHERE category = ? AND rule = ?', (category, rule)
    ).fetchone()
    if existing:
        conn.execute(
            '''UPDATE preferences SET evidence_count = ?, confidence = ?, last_updated = ?
               WHERE id = ?''',
            (evidence_count, confidence, now, existing['id'])
        )
    else:
        conn.execute(
            '''INSERT INTO preferences (category, rule, evidence_count, confidence,
               first_observed, last_updated, active) VALUES (?, ?, ?, ?, ?, ?, 1)''',
            (category, rule, evidence_count, confidence, now, now)
        )
    conn.commit()
    conn.close()


def get_preferences(category: str = None) -> list:
    conn = get_conn()
    if category:
        rows = conn.execute(
            'SELECT * FROM preferences WHERE active = 1 AND category = ? ORDER BY confidence DESC', (category,)
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT * FROM preferences WHERE active = 1 ORDER BY confidence DESC'
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(standing_instructions: str = '') -> int:
    now = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        'INSERT INTO sessions (started_at, standing_instructions) VALUES (?, ?)',
        (now, standing_instructions)
    )
    sid = c.lastrowid
    conn.commit()
    conn.close()
    return sid


def end_session(id: int, stats: dict):
    now = datetime.datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute(
        '''UPDATE sessions SET ended_at = ?, contacts_found = ?, messages_sent = ?,
           preferences_updated = ? WHERE id = ?''',
        (now, stats.get('contacts_found', 0), stats.get('messages_sent', 0),
         stats.get('preferences_updated', 0), id)
    )
    conn.commit()
    conn.close()


def get_session(id: int) -> dict:
    conn = get_conn()
    row = conn.execute('SELECT * FROM sessions WHERE id = ?', (id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Checkpoints ───────────────────────────────────────────────────────────────

def save_checkpoint(agent_id, job_id, session_id, ctx_json, tool_step):
    conn = get_conn()
    conn.execute(
        '''INSERT INTO agent_checkpoints (agent_id, job_id, session_id, ctx_json, tool_step)
           VALUES (?, ?, ?, ?, ?)''',
        (agent_id, job_id, session_id, ctx_json, tool_step)
    )
    conn.commit()
    conn.close()


def get_latest_checkpoint(agent_id, job_id, session_id):
    conn = get_conn()
    row = conn.execute(
        '''SELECT ctx_json FROM agent_checkpoints
           WHERE agent_id=? AND job_id=? AND session_id=?
           ORDER BY created_at DESC LIMIT 1''',
        (agent_id, job_id, session_id)
    ).fetchone()
    conn.close()
    return row['ctx_json'] if row else None


# ── Failure log ───────────────────────────────────────────────────────────────

def log_failure(agent_id, job_id, session_id, failure_type, severity, action_taken,
                detail="", recovered=False):
    """Log a failure event. Never raises."""
    try:
        conn = get_conn()
        conn.execute(
            '''INSERT INTO agent_failures
               (agent_id, job_id, session_id, failure_type, severity, action_taken, detail, recovered)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (agent_id, job_id, session_id, failure_type, severity, action_taken, detail, recovered)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


if __name__ == '__main__':
    init_db()
