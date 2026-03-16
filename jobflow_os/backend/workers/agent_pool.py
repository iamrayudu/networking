import logging
import os
import pickle
import threading
from requests.cookies import RequestsCookieJar
from backend.agents.linkedin_agent import LinkedInAgent
from backend.memory.database import create_session
from backend.config import cfg

logger = logging.getLogger(__name__)


def _read_cookies_from_chrome() -> tuple:
    """Read li_at + JSESSIONID directly from Chrome's local cookie store.
    Decrypts using the macOS Keychain key — no user action needed.
    Returns (li_at, jsessionid) or ('', '') if unavailable."""
    try:
        from pycookiecheat import chrome_cookies
        cookies = chrome_cookies('https://www.linkedin.com')
        li_at = cookies.get('li_at', '')
        jsessionid = cookies.get('JSESSIONID', '')
        if li_at and jsessionid:
            logger.info('AgentPool: read li_at + JSESSIONID directly from Chrome cookie store')
            return li_at, jsessionid
        logger.warning('AgentPool: Chrome cookies found but li_at/JSESSIONID missing — not logged into LinkedIn in Chrome?')
        return '', ''
    except Exception as e:
        logger.warning(f'AgentPool: could not read Chrome cookies — {e}')
        return '', ''


def _inject_browser_cookies(email: str, li_at: str, jsessionid: str):
    """Write browser cookies into the linkedin-api cookie cache.
    This lets the library skip the /uas/authenticate call entirely — no CHALLENGE possible."""
    cookie_dir = os.path.expanduser('~/.linkedin_api/cookies/')
    os.makedirs(cookie_dir, exist_ok=True)
    jar = RequestsCookieJar()
    jar.set('li_at', li_at, domain='.linkedin.com', path='/')
    # LinkedIn expects JSESSIONID with surrounding quotes in the header
    jsid = jsessionid if jsessionid.startswith('"') else f'"{jsessionid}"'
    jar.set('JSESSIONID', jsid, domain='.linkedin.com', path='/')
    cookie_path = os.path.join(cookie_dir, f'{email}.jr')
    with open(cookie_path, 'wb') as f:
        pickle.dump(jar, f)
    logger.info(f'AgentPool: browser cookies injected → {cookie_path}')


def _persist_cookies_to_config(li_at: str, li_jsessionid: str):
    """Write fresh cookies back to config.yaml so next restart picks them up."""
    import re
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')
    config_path = os.path.normpath(config_path)
    try:
        with open(config_path, 'r') as f:
            text = f.read()
        text = re.sub(r"(li_at:\s*)['\"]?[^'\"\n]*['\"]?", f"li_at: '{li_at}'", text)
        text = re.sub(r"(li_jsessionid:\s*)['\"]?[^'\"\n]*['\"]?", f"li_jsessionid: '{li_jsessionid}'", text)
        with open(config_path, 'w') as f:
            f.write(text)
        # Update in-memory config too
        cfg.setdefault('linkedin', {})['li_at'] = li_at
        cfg.setdefault('linkedin', {})['li_jsessionid'] = li_jsessionid
        logger.info('AgentPool: cookies persisted to config.yaml')
    except Exception as e:
        logger.warning(f'AgentPool: could not persist cookies to config.yaml — {e}')


def _login_linkedin() -> object:
    """Authenticate once and return a shared Linkedin API instance.

    Priority:
    1. LI_AT + LI_JSESSIONID env vars → inject browser cookies, skip auth request entirely
    2. EMAIL + PASSWORD env vars → normal programmatic login (may trigger CHALLENGE)
    """
    li_cfg = cfg.get('linkedin', {})
    email    = os.environ.get('EMAIL')    or li_cfg.get('email', '')
    password = os.environ.get('PASSWORD') or li_cfg.get('password', '')

    if not email:
        logger.error('AgentPool: linkedin.email not set in config.yaml')
        return None

    # Priority 1: read directly from Chrome cookie store — fully automatic, no copy-paste
    li_at, jsessionid = _read_cookies_from_chrome()

    # Priority 2: fall back to config.yaml / env vars
    if not (li_at and jsessionid):
        li_at      = os.environ.get('LI_AT')         or li_cfg.get('li_at', '')
        jsessionid = os.environ.get('LI_JSESSIONID') or li_cfg.get('li_jsessionid', '')
        if li_at and jsessionid:
            logger.info('AgentPool: using li_at + jsessionid from config.yaml')

    # Inject whichever cookies we have — bypasses /uas/authenticate entirely
    if li_at and jsessionid:
        _inject_browser_cookies(email, li_at, jsessionid)
        _persist_cookies_to_config(li_at, jsessionid)
    else:
        logger.warning(
            'AgentPool: no browser cookies available — falling back to email/password '
            '(may trigger CHALLENGE). Make sure Chrome is open and logged into LinkedIn.'
        )

    try:
        from linkedin_api import Linkedin
        li_api = Linkedin(email, password or 'unused_when_cookies_cached')
        logger.info('AgentPool: LinkedIn session ready — shared across all agents')
        return li_api
    except Exception as e:
        err = str(e)
        logger.error(f'AgentPool: LinkedIn login failed — {err}')
        if 'CHALLENGE' in err.upper() or 'challenge' in err.lower():
            logger.error(
                'AgentPool: CHALLENGE — open Chrome, log into linkedin.com, then restart. '
                'The app will auto-read the cookies next time.'
            )
        return None


class AgentPool:
    def __init__(self):
        self.agents: dict = {}
        self.threads: dict = {}
        self.current_session_id = None
        self._li_api = None          # shared LinkedIn session
        self._li_lock = threading.Lock()

    def _get_or_login(self) -> object:
        """Return existing shared li_api or create a new one (thread-safe)."""
        with self._li_lock:
            if self._li_api is not None:
                return self._li_api
            self._li_api = _login_linkedin()
            return self._li_api

    def invalidate_session(self):
        """Called by an agent when it detects the session is expired/rejected."""
        with self._li_lock:
            self._li_api = None
            logger.info('AgentPool: shared LinkedIn session invalidated — next agent will re-login')

    def start_session(self, job_ids: list, standing_instructions: str = '') -> int:
        # Stop any running agents from previous session
        for agent in self.agents.values():
            agent.stop_flag.set()
            agent.approval_event.set()
        self.agents = {}
        self.threads = {}

        # Login once upfront — all agents share this instance
        li_api = self._get_or_login()
        if li_api is None:
            logger.error('AgentPool: cannot start session — LinkedIn login failed')
            return -1

        session_id = create_session(standing_instructions)
        self.current_session_id = session_id
        max_agents = cfg['agents']['max_parallel_agents']

        for job_id in job_ids[:max_agents]:
            agent_id = f'agent_{job_id}_{session_id}'
            agent = LinkedInAgent(agent_id, job_id, session_id)
            agent.li_api = li_api          # inject shared session
            if standing_instructions:
                agent.standing_instructions = standing_instructions
            self.agents[agent_id] = agent
            t = threading.Thread(target=self._run_agent, args=(agent,), daemon=True)
            self.threads[agent_id] = t
            t.start()

        return session_id

    def _run_agent(self, agent: LinkedInAgent):
        agent.start()
        # Check if all agents done → run preference update
        all_done = all(not t.is_alive() for t in self.threads.values())
        if all_done:
            self.on_all_complete()

    def refresh_cookies(self, li_at: str = '', li_jsessionid: str = '') -> bool:
        """Called when user submits fresh browser cookies via the UI.
        Re-injects cookies, rebuilds the shared li_api, notifies all waiting agents,
        and persists the new cookies to config.yaml."""
        li_cfg = cfg.get('linkedin', {})
        email = os.environ.get('EMAIL') or li_cfg.get('email', '')
        if not email:
            logger.error('AgentPool.refresh_cookies: no email set')
            return False

        # Try Chrome auto-read first — user may have already re-logged in their browser
        chrome_at, chrome_jsid = _read_cookies_from_chrome()
        if chrome_at and chrome_jsid:
            logger.info('AgentPool.refresh_cookies: fresh cookies auto-read from Chrome')
            li_at, li_jsessionid = chrome_at, chrome_jsid

        if not (li_at and li_jsessionid):
            logger.error('AgentPool.refresh_cookies: no cookies available from Chrome or UI input')
            return False

        # 1. Inject the new cookies into the linkedin-api cache
        _inject_browser_cookies(email, li_at, li_jsessionid)

        # 2. Re-create the shared li_api with the fresh cookies
        with self._li_lock:
            self._li_api = None  # force re-login
        new_api = self._get_or_login()
        if new_api is None:
            logger.error('AgentPool.refresh_cookies: re-login failed after cookie inject')
            return False

        # 3. Push new session to all active agents and unblock any waiting for refresh
        for agent in self.agents.values():
            agent.li_api = new_api
            agent.cookie_refresh_event.set()

        # 4. Persist to config.yaml so next restart picks them up automatically
        _persist_cookies_to_config(li_at, li_jsessionid)

        logger.info('AgentPool.refresh_cookies: cookies refreshed — all agents notified')
        return True

    def notify_agent(self, agent_id: str, action: str, data: dict):
        agent = self.agents.get(agent_id)
        if agent:
            agent.approval_result = action
            agent.approval_data = data
            agent.approval_event.set()

    def route_user_reply(self, agent_id: str, message: str):
        agent = self.agents.get(agent_id)
        if agent:
            agent.user_reply = message
            agent.approval_event.set()

    def broadcast_instruction(self, instruction: str):
        for agent in self.agents.values():
            agent.emit('AGENT_MESSAGE', {
                'message': f'Standing instruction received: {instruction}. Applying now.'
            })
            agent.standing_instructions = (
                getattr(agent, 'standing_instructions', '') + '\n' + instruction
            )

    def apply_standing_instruction(self, instruction: str, scope: str):
        if scope == 'ALL':
            self.broadcast_instruction(instruction)
        else:
            self.route_user_reply(scope, instruction)

    def pause_agent(self, agent_id: str):
        agent = self.agents.get(agent_id)
        if agent:
            agent.pause_flag.set()

    def resume_agent(self, agent_id: str):
        agent = self.agents.get(agent_id)
        if agent:
            agent.pause_flag.clear()

    def pause_all_agents(self):
        for agent in self.agents.values():
            agent.pause_flag.set()

    def stop_agent(self, agent_id: str):
        agent = self.agents.get(agent_id)
        if agent:
            agent.stop_flag.set()
            agent.approval_event.set()  # Unblock if waiting for approval

    def get_all_status(self) -> list:
        return [
            {'agent_id': aid, 'status': a.stats, 'job_id': a.job_id}
            for aid, a in self.agents.items()
        ]

    def on_all_complete(self):
        from backend.workers.preference_updater import run_preference_update
        if self.current_session_id:
            run_preference_update(self.current_session_id)


pool = AgentPool()
