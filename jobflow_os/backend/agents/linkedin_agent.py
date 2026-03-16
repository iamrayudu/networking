import logging
import time
import random
import threading
import uuid
import os

logger = logging.getLogger(__name__)

from backend.memory.context_object import (
    build_initial_context, reset_for_next_person,
    checkpoint, restore_checkpoint, is_duplicate, mark_contacted
)
from backend.memory.observation_categories import add_observation
from backend.memory.database import log_agent_action, insert_contact, update_contact_status
from backend.memory.vector_store import embed
from backend.memory.voice_anchor import prepend_voice_anchor
from backend.agents.message_agent import score_contact, draft_message
from backend.agents.contact_agent import send_invite
from backend.agents.failure_handler import handle_failure
from backend.websocket_manager import ws_manager
from backend.core.claude_client import ask
from backend.config import cfg


class LinkedInAgent:
    def __init__(self, agent_id: str, job_id: int, session_id: int):
        self.agent_id = agent_id
        self.job_id = job_id
        self.session_id = session_id
        self.li_api = None
        self.standing_instructions = ''
        self.stop_flag = threading.Event()
        self.pause_flag = threading.Event()
        self.approval_event = threading.Event()
        self.approval_result = None
        self.approval_data = None
        self.user_reply = None
        self.cookie_refresh_event = threading.Event()
        self.stats = {'found': 0, 'sent': 0, 'skipped': 0}

    def emit(self, event_type: str, payload: dict):
        try:
            ws_manager.broadcast_sync(event_type, {'agent_id': self.agent_id, **payload})
        except Exception as e:
            logger.warning(f'[{self.agent_id}] emit failed ({event_type}): {e}')

    def log(self, func: str, action: str, detail: str, status: str = 'SUCCESS'):
        db_action = f'LinkedInAgent.{func} → {action}'
        log_agent_action(self.agent_id, self.job_id, self.session_id, db_action, detail, status)
        _log = logging.getLogger(f'LinkedInAgent.{func}')
        msg = f'[{self.agent_id}] {detail}'
        if status == 'ERROR':
            _log.error(msg)
        elif status == 'FAILED':
            _log.warning(msg)
        else:
            _log.info(msg)

    def start(self):
        try:
            # 1. Restore or build context
            ctx = restore_checkpoint(self.agent_id, self.job_id, self.session_id)
            if ctx:
                last_step = ctx["session"]["actions_taken"][-1]["step"] if ctx["session"]["actions_taken"] else "start"
                self.emit('AGENT_MESSAGE', {'message': f'Resuming from checkpoint: {last_step}'})
            else:
                try:
                    ctx = build_initial_context(self.job_id, self.session_id)
                except FileNotFoundError:
                    handle_failure("missing_profile_file", self, {})
                    return
                except ValueError:
                    job = {}
                    try:
                        from backend.memory.database import get_job
                        job = get_job(self.job_id) or {}
                    except Exception:
                        pass
                    handle_failure("missing_enrichment", self, {},
                                   company=job.get("company", ""),
                                   role=job.get("role_title", ""))
                    return
                ctx["session"]["agent_id"] = self.agent_id

            if self.standing_instructions:
                ctx["session"]["standing_instructions"] = self.standing_instructions

            checkpoint(ctx)
            job_info = ctx["permanent"]["role"]
            company = job_info.get('company', '')
            role_title = job_info.get('role_title', '')
            self.log('start', 'CONTEXT_READY', f'Context built for {company} — {role_title}')
            self.emit('AGENT_STATUS', {'status': 'running', 'current_action': 'Loading context', 'company': company, 'role': role_title})

            # 2. Opening briefing
            briefing_system = prepend_voice_anchor(
                ctx,
                "Write a 2-3 sentence agent briefing. Be specific about the role and one key finding. "
                "Name the company, the role, and what you plan to do next."
            )
            briefing = ask(
                f"Briefing for: {company} — {role_title}. "
                f"Enrichment summary: {str(ctx['permanent']['enrichment'])[:500]}",
                system=briefing_system
            )
            self.emit('AGENT_BRIEFING', {'phase': 'starting', 'message': briefing})

            # 3. Connect to LinkedIn API
            # li_api is injected by AgentPool (shared session — only one login per session).
            # If for some reason it wasn't injected, fall back to logging in here.
            if self.li_api is None:
                email = os.environ.get('EMAIL') or cfg.get('linkedin', {}).get('email', '')
                password = os.environ.get('PASSWORD') or cfg.get('linkedin', {}).get('password', '')
                if not email or not password:
                    self.emit('AGENT_MESSAGE', {
                        'message': '⚠️ No LinkedIn credentials found. Set EMAIL and PASSWORD and restart.'
                    })
                    self.log('start', 'NO_CREDENTIALS', 'EMAIL/PASSWORD not set', 'FAILED')
                    return
                self.emit('AGENT_STATUS', {'status': 'running', 'current_action': 'Connecting to LinkedIn...'})
                try:
                    from linkedin_api import Linkedin
                    self.li_api = Linkedin(email, password)
                    self.log('start', 'LOGIN_OK', 'linkedin-api authenticated successfully')
                except Exception as e:
                    err = str(e)
                    self.log('start', 'LOGIN_FAILED', f'LinkedIn auth failed: {err}', 'FAILED')
                    if 'CHALLENGE' in err.upper() or 'challenge' in err.lower():
                        self.emit('AGENT_MESSAGE', {
                            'message': (
                                '⚠️ LinkedIn requires verification.\n\n'
                                '1. Open linkedin.com in your browser\n'
                                '2. Log in and complete the security check / 2FA\n'
                                '3. Restart the backend server and launch the agent again'
                            )
                        })
                    else:
                        self.emit('AGENT_MESSAGE', {'message': f'LinkedIn login failed: {err}'})
                    return

            self.emit('AGENT_MESSAGE', {'message': 'Connected to LinkedIn.'})

            # 4. Search people at target company
            self.emit('AGENT_STATUS', {'status': 'running', 'current_action': f'Searching for people at {company}'})
            self.emit('AGENT_MESSAGE', {'message': f'Searching LinkedIn for people at {company}...'})
            candidates, ctx = self.search_people(ctx)

            if not candidates:
                self.emit('AGENT_MESSAGE', {'message': f'No candidates found for {company}. Ending session.'})
                self.emit('PHASE_COMPLETE', {'phase': 'networking', 'summary_stats': self.stats})
                return

            self.emit('AGENT_MESSAGE', {
                'message': f'Found {len(candidates)} candidate profiles at {company}. Evaluating each one...'
            })

            # 5. Process each candidate
            for candidate in candidates:
                if self.stop_flag.is_set():
                    break
                while self.pause_flag.is_set():
                    time.sleep(1)

                self.emit('AGENT_STATUS', {'status': 'running', 'current_action': f'Reading profile: {candidate["name"]}'})
                self.emit('AGENT_MESSAGE', {'message': f'Reading profile: **{candidate["name"]}** — {candidate.get("title", "")}'})

                profile, ctx = self.read_profile(candidate, ctx)
                if not profile:
                    self.emit('AGENT_MESSAGE', {'message': f'Skipped {candidate["name"]} — profile not readable.'})
                    ctx = reset_for_next_person(ctx)
                    checkpoint(ctx)
                    continue

                # Standing instruction: skip recruiters
                if ctx["session"]["standing_instructions"] and 'recruiter' in profile.get('title', '').lower():
                    if 'skip recruiter' in ctx["session"]["standing_instructions"].lower():
                        self.emit('AGENT_MESSAGE', {'message': f'Skipped {profile["name"]} — recruiter (standing instruction).'})
                        ctx = reset_for_next_person(ctx)
                        checkpoint(ctx)
                        continue

                self.emit('AGENT_STATUS', {'status': 'running', 'current_action': f'Scoring {profile["name"]}'})
                scored, ctx = self.score_and_checkpoint(ctx)

                if scored['score'] < cfg['agents']['relevance_min_score']:
                    self.emit('AGENT_MESSAGE', {
                        'message': f'Scored {profile["name"]}: {scored["score"]}/10 — too low, skipping. ({scored["reason"]})'
                    })
                    ctx = reset_for_next_person(ctx)
                    checkpoint(ctx)
                    continue

                self.emit('AGENT_MESSAGE', {
                    'message': f'✓ {profile["name"]} scored {scored["score"]}/10 — good match! Drafting message...'
                })
                self.stats['found'] += 1
                message_draft_result = draft_message(ctx)

                contact_id = insert_contact({
                    'job_id': self.job_id,
                    'session_id': self.session_id,
                    'full_name': profile['name'],
                    'linkedin_url': profile['linkedin_url'],
                    'title': profile['title'],
                    'relevance_score': scored['score'],
                    'relevance_reason': scored['reason'],
                    'invite_message': message_draft_result.get('draft_a', ''),
                    'status': 'PENDING_APPROVAL',
                    'agent_id': self.agent_id,
                    'chroma_id': None,
                })

                self.request_approval(contact_id, profile, scored, message_draft_result, ctx)

                if self.stop_flag.is_set():
                    break

                ctx = reset_for_next_person(ctx)
                checkpoint(ctx)
                time.sleep(random.uniform(2, 4))  # polite rate limiting

            # 6. Done
            self.emit('PHASE_COMPLETE', {'phase': 'networking', 'summary_stats': self.stats})
            self.emit('AGENT_MESSAGE', {
                'message': (
                    f"Session complete. "
                    f"Found: {self.stats['found']}, "
                    f"Sent: {self.stats['sent']}, "
                    f"Skipped: {self.stats['skipped']}"
                )
            })

        except Exception as e:
            import traceback
            err_detail = traceback.format_exc()
            logger.error(f'[{self.agent_id}] AGENT_ERROR: {e}\n{err_detail}')
            self.log('start', 'AGENT_ERROR', str(e)[:500], 'FAILED')
            self.emit('ERROR', {'error_type': 'AGENT_ERROR', 'message': str(e), 'recoverable': False})

    def search_people(self, ctx: dict):
        try:
            from backend.memory.database import get_job
            job = get_job(self.job_id) or {}
            company = job.get('company', '')
            limit = cfg['agents']['contacts_per_company'] * 3

            # Search multiple relevant title types to get useful people
            TARGET_TITLES = [
                'Product Manager', 'Engineering Manager', 'Director',
                'Recruiter', 'Talent', 'VP', 'Senior Manager',
            ]
            seen_urns = set()
            candidates = []

            for title_kw in TARGET_TITLES:
                if len(candidates) >= limit:
                    break
                try:
                    batch = self.li_api.search_people(
                        keyword_company=company,
                        keyword_title=title_kw,
                        limit=5,
                    )
                    for r in batch:
                        urn_id = r.get('urn_id', '').strip()
                        name = r.get('name', '').strip()
                        if not urn_id or not name or urn_id in seen_urns:
                            continue
                        seen_urns.add(urn_id)
                        candidates.append({
                            'name': name,
                            'urn_id': urn_id,
                            'title': r.get('jobtitle') or '',
                            'distance': r.get('distance', 'DISTANCE_3'),
                        })
                except Exception:
                    continue

            self.log('search_people', 'RAW_RESULTS', f'Found {len(candidates)} targeted candidates at "{company}"')

            if not candidates:
                self.log('search_people', 'NO_RESULTS', f'No candidates for "{company}"', 'FAILED')
                self.emit('AGENT_MESSAGE', {'message': f'No people found at {company} via LinkedIn API.'})
                return ([], ctx)

            self.log('search_people', 'FOUND', f'{len(candidates)} candidates for "{company}"')
            ctx["session"]["candidates_found"] = candidates
            checkpoint(ctx)
            return (candidates, ctx)

        except Exception as e:
            self.log('search_people', 'EXCEPTION', f'Search error: {e}', 'ERROR')
            self.emit('AGENT_MESSAGE', {'message': f'Search failed: {e}'})
            return ([], ctx)

    def read_profile(self, candidate: dict, ctx: dict):
        """Build profile directly from search result — no extra API call needed."""
        urn_id = candidate['urn_id']
        name = candidate['name']

        linkedin_url = f'https://www.linkedin.com/search/results/people/?keywords={name.replace(" ", "%20")}&urn={urn_id}'
        if is_duplicate(linkedin_url, ctx):
            self.log('read_profile', 'SKIP_DUPLICATE', f'Already contacted — skipping {name}', 'SKIPPED')
            return (None, ctx)

        # Parse title and company out of jobtitle string
        # Handles: "Sr Engineer @ Oracle", "Sr Engineer at Oracle", "Sr Engineer - Oracle"
        raw_title = candidate.get('title', '')
        import re as _re
        sep = _re.search(r'\s+[@at\-]\s+', raw_title)
        if sep:
            title = raw_title[:sep.start()].strip()
            exp_company = raw_title[sep.end():].split(' | ')[0].split(' |')[0].strip()
        else:
            title = raw_title
            exp_company = ''

        distance = candidate.get('distance', 'DISTANCE_3')
        degree_map = {'DISTANCE_1': '1st', 'DISTANCE_2': '2nd', 'DISTANCE_3': '3rd'}
        connection_degree = degree_map.get(distance, '3rd')

        profile = {
            'name': name,
            'title': title,
            'headline': raw_title,
            'summary': '',
            'company': exp_company,
            'linkedin_url': linkedin_url,
            'urn_id': urn_id,
            'mutual_connections': 0,
            'connection_degree': connection_degree,
            'past_roles': [],
            'recent_activity': None,
            'skills_visible': [],
            'current_role_duration': None,
        }

        from backend.memory.output_schemas import validate_step
        profile = validate_step(profile, "profile")
        ctx["current_person"].update(profile)

        # Observations from title text
        combined = raw_title.lower()
        if any(kw in combined for kw in ['ai', 'automation', 'agent', 'ml', 'llm', 'machine learning']):
            ctx = add_observation(ctx, "profile_read", "AI_SIGNAL", f"title mentions AI: {raw_title[:80]}")
        if any(kw in combined for kw in ['data', 'analytics', 'pipeline']):
            ctx = add_observation(ctx, "profile_read", "DATA_SIGNAL", "title mentions data/analytics")
        if any(kw in combined for kw in ['engineer', 'developer', 'architect', 'builder']):
            ctx = add_observation(ctx, "profile_read", "BUILDER_SIGNAL", "engineering background")

        self.log('read_profile', 'BUILT',
                 f'name={name!r} title={title!r} degree={connection_degree}')
        checkpoint(ctx)
        return (profile, ctx)

    def score_and_checkpoint(self, ctx: dict):
        person = ctx['current_person']
        self.log('score_and_checkpoint', 'SCORING',
                 f'Scoring {person.get("name")} ({person.get("title")})')
        scored = score_contact(ctx)
        ctx["current_score"]["score"] = scored.get("score", 0)
        ctx["current_score"]["reason"] = scored.get("reason", "")
        ctx["current_score"]["fit_angle"] = scored.get("fit_angle", "")
        ctx["current_score"]["hook_source"] = scored.get("hook_source", "role_signal")
        self.log('score_and_checkpoint', 'SCORE_RESULT',
                 f'{person.get("name")} → score={scored.get("score")}/10 | {scored.get("reason", "")[:120]}')
        checkpoint(ctx)
        return (scored, ctx)

    def _emit_approval_card(self, contact_id, profile, scored, draft):
        self.emit('APPROVAL_REQUEST', {
            'contact_id': contact_id,
            'person': {
                'name': profile['name'],
                'title': profile['title'],
                'linkedin_url': profile['linkedin_url'],
                'mutual_connections': profile.get('mutual_connections', 0),
            },
            'message_draft': draft,
            'message_draft_b': '',
            'recommended': 'A',
            'relevance': scored['score'],
            'reason': scored['reason'],
            'session_id': self.session_id,
            'agent_id': self.agent_id,
            'context_snapshot': {
                'job_id': self.job_id,
                'company': profile.get('company', ''),
                'person_title': profile['title'],
                'relevance_score': scored['score'],
                'contact_id': contact_id,
            },
        })

    def request_approval(self, contact_id: int, profile: dict, scored: dict,
                         message_draft_result: dict, ctx: dict):
        import json as _json

        draft = message_draft_result.get('draft_a', '')
        self._emit_approval_card(contact_id, profile, scored, draft)
        self.emit('AGENT_STATUS', {'status': 'waiting', 'current_action': f'Waiting for your input on {profile["name"]}'})
        self.emit('AGENT_MESSAGE', {
            'message': (
                f'I found **{profile["name"]}** — {profile["title"]} (score {scored["score"]}/10).\n\n'
                f'Here\'s the draft message above. You can:\n'
                f'• Click **Approve & Send** to send it\n'
                f'• Click **Skip** to move on\n'
                f'• Type here to guide me — e.g. "make it shorter", "change the tone", "skip this one"'
            )
        })
        self.log('request_approval', 'WAITING', f'Waiting on {profile["name"]}')

        # Conversation loop — keep going until a hard decision
        while not self.stop_flag.is_set():
            self.approval_event.clear()
            self.approval_result = None
            self.user_reply = None

            self.approval_event.wait(timeout=3600)

            # Hard button decisions
            if self.approval_result in ('approve', 'edit'):
                final_message = (self.approval_data or {}).get('final_message', draft)
                self._do_send(contact_id, profile, final_message, ctx)
                break

            if self.approval_result == 'skip':
                self.stats['skipped'] += 1
                self.emit('AGENT_MESSAGE', {'message': f'Skipped {profile["name"]}.'})
                self.log('request_approval', 'SKIPPED', f'User skipped {profile["name"]}', 'SKIPPED')
                break

            # User typed a message — handle conversationally
            if self.user_reply:
                user_text = self.user_reply.strip()
                self.emit('AGENT_STATUS', {'status': 'running', 'current_action': 'Thinking...'})

                try:
                    guidance_response = ask(
                        f"""You are helping review a LinkedIn connection request draft.

Person: {profile['name']} — {profile['title']}
Score: {scored['score']}/10 — {scored['reason']}

Current draft:
"{draft}"

The user just said: "{user_text}"

Decide what to do and respond with ONLY valid JSON (no markdown):
- If user wants to SKIP this person: {{"action": "skip", "reply": "..."}}
- If user wants to REVISE the draft: {{"action": "revise", "new_draft": "...", "reply": "..."}}
- If user wants to SEND as-is: {{"action": "approve", "reply": "..."}}
- If user is giving general guidance or asking a question: {{"action": "respond", "reply": "..."}}"""
                    )

                    result = _json.loads(guidance_response.strip().strip('`').replace('```json', '').replace('```', '').strip())
                    action = result.get('action', 'respond')
                    reply = result.get('reply', 'Understood.')

                    if action == 'skip':
                        self.stats['skipped'] += 1
                        self.emit('AGENT_MESSAGE', {'message': reply})
                        self.log('request_approval', 'SKIPPED', f'User-guided skip: {profile["name"]}', 'SKIPPED')
                        break

                    elif action == 'approve':
                        self.emit('AGENT_MESSAGE', {'message': reply})
                        self._do_send(contact_id, profile, draft, ctx)
                        break

                    elif action == 'revise':
                        draft = result.get('new_draft', draft)
                        self.emit('AGENT_MESSAGE', {'message': reply})
                        self._emit_approval_card(contact_id, profile, scored, draft)
                        self.emit('AGENT_STATUS', {'status': 'waiting', 'current_action': f'Waiting for your input on {profile["name"]}'})
                        # loop continues — wait for next input

                    else:  # respond / anything else
                        self.emit('AGENT_MESSAGE', {'message': reply})
                        self.emit('AGENT_STATUS', {'status': 'waiting', 'current_action': f'Waiting for your input on {profile["name"]}'})
                        # loop continues

                except Exception:
                    self.emit('AGENT_MESSAGE', {'message': f'Let me know: approve, skip, or tell me how to change the message.'})
                    self.emit('AGENT_STATUS', {'status': 'waiting', 'current_action': f'Waiting for your input on {profile["name"]}'})

                continue

            # Timeout — move on
            self.emit('AGENT_MESSAGE', {'message': f'No response for {profile["name"]} — moving on.'})
            break

        self.emit('AGENT_STATUS', {'status': 'running', 'current_action': 'Continuing...'})

    def _relogin(self, email: str) -> bool:
        """Session expired — pause, emit a cookie refresh card in the UI, wait up to 10 min.
        Returns True if the user provided fresh cookies in time, False otherwise."""
        import os as _os
        cookie_path = _os.path.expanduser(f'~/.linkedin_api/cookies/{email}.jr')
        if _os.path.exists(cookie_path):
            _os.remove(cookie_path)

        from backend.workers.agent_pool import pool
        pool.invalidate_session()

        self.log('relogin', 'COOKIE_REFRESH_NEEDED', 'Waiting for user to provide fresh cookies')
        self.cookie_refresh_event.clear()

        # Emit a special event — frontend renders a cookie input card in this agent's chat
        self.emit('COOKIE_REFRESH_REQUIRED', {
            'message': '⚠️ LinkedIn session expired. Paste fresh cookies below to resume.'
        })
        self.emit('AGENT_STATUS', {
            'status': 'waiting',
            'current_action': 'Waiting for cookie refresh'
        })

        # Block until user submits cookies (or 10 min timeout)
        refreshed = self.cookie_refresh_event.wait(timeout=600)
        self.cookie_refresh_event.clear()

        if refreshed:
            self.li_api = pool._li_api  # pick up the new shared session
            self.log('relogin', 'COOKIE_REFRESHED', 'Cookies refreshed — retrying send')
            self.emit('AGENT_STATUS', {'status': 'running', 'current_action': 'Retrying send...'})
            return True

        self.log('relogin', 'COOKIE_REFRESH_TIMEOUT', 'No cookies provided in time', 'FAILED')
        self.emit('AGENT_MESSAGE', {'message': '⏱ Cookie refresh timed out — skipping this contact.'})
        return False

    def _do_send(self, contact_id, profile, final_message, ctx):
        result = send_invite(self.li_api, profile['urn_id'], final_message)

        # Session expired — delete cookie cache, re-login once, retry
        if result.get('reason') == 'session_expired_relogin':
            email = os.environ.get('EMAIL') or cfg.get('linkedin', {}).get('email', '')
            self.log('request_approval', 'SESSION_EXPIRED', 'Stale cookie — invalidating session')
            if self._relogin(email):
                result = send_invite(self.li_api, profile['urn_id'], final_message)
            else:
                result = {'sent': False, 'reason': 'relogin_failed'}

        if result.get('sent'):
            update_contact_status(contact_id, 'SENT')
            chroma_id = str(uuid.uuid4())
            embed('jobflow_messages', chroma_id, final_message, {
                'job_id': self.job_id,
                'title': profile['title'],
                'company': profile.get('company', ''),
            })
            ctx = mark_contacted(profile['linkedin_url'], ctx)
            checkpoint(ctx)
            self.stats['sent'] += 1
            self.emit('AGENT_MESSAGE', {'message': f'✓ Connection request sent to {profile["name"]}!'})
            self.log('request_approval', 'SENT', f'SENT ✓ — {profile["name"]}')
        else:
            reason = result.get('reason', 'unknown')
            self.emit('AGENT_MESSAGE', {'message': f'Could not send to {profile["name"]}: {reason}'})
            self.log('request_approval', 'SEND_FAILED', f'Failed — {reason}', 'FAILED')
            if reason == 'already_connected':
                ctx = mark_contacted(profile['linkedin_url'], ctx)
