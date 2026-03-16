import logging
from backend.core.claude_client import ask_json
from backend.skills.skill_loader import inject_skill_as_system
from backend.memory.observation_categories import has_observation, get_observations_by_category
from backend.memory.output_schemas import validate_step
from backend.memory.database import log_agent_action

logger = logging.getLogger(__name__)

LINKEDIN_CHAR_LIMIT = 300

BANNED_PHRASES = [
    "i hope this finds you",
    "i hope this message finds you",
    "i'd love to",
    "i would love to",
    "i came across your profile",
    "i was impressed",
    "i'm passionate",
    "excited to connect",
    "i'd be honored",
    "looking forward to hearing",
    "exploring new opportunities",
    "open to new challenges",
    "results-driven",
    "proven track record",
]


def trim_to_limit(draft: str, limit: int = LINKEDIN_CHAR_LIMIT) -> str:
    if len(draft) <= limit:
        return draft
    trimmed = draft[:limit]
    last_space = trimmed.rfind(" ")
    if last_space > limit * 0.8:
        trimmed = trimmed[:last_space]
    return trimmed.rstrip(" .,")


def check_voice_drift(draft: str) -> list:
    """Returns list of banned phrases found (empty list = pass). Case-insensitive."""
    draft_lower = draft.lower()
    return [phrase for phrase in BANNED_PHRASES if phrase in draft_lower]


def fix_drift(draft: str, violations: list, ctx: dict) -> str:
    """Makes ONE correction Claude call to remove banned phrases."""
    from backend.memory.voice_anchor import prepend_voice_anchor
    from backend.core.claude_client import ask
    target_length = LINKEDIN_CHAR_LIMIT
    system = prepend_voice_anchor(ctx,
        f"Rewrite this message removing these exact phrases: {violations}. "
        f"Keep the same hook and structure. Keep under {target_length} chars. "
        f"Return only the rewritten message text."
    )
    try:
        fixed = ask(draft, system=system, max_tokens=200)
        remaining = check_voice_drift(fixed)
        if remaining:
            logger.warning(f"Voice drift persists after fix: {remaining}")
        return fixed.strip()
    except Exception as e:
        logger.warning(f"fix_drift failed: {e}")
        return draft


def score_contact(ctx: dict) -> dict:
    person = ctx["current_person"]
    p = ctx["permanent"]
    job_id = ctx.get("session", {}).get("job_id", 0)
    session_id = ctx.get("session", {}).get("session_id", 0)

    _score_log = logging.getLogger('message_agent.score_contact')
    _score_log.info(f'Scoring {person.get("name","?")} ({person.get("title","?")} @ {person.get("company","?")})'
                    f' — {person.get("connection_degree","?")} degree, {person.get("mutual_connections",0)} mutuals')
    log_agent_action('message_agent', job_id, session_id,
                     'message_agent.score_contact → SCORING',
                     f'{person.get("name","?")} | {person.get("title","?")} | degree={person.get("connection_degree","?")}')

    prompt = (
        f"ROLE: {p['role']['company']} — {p['role']['role_title']}\n\n"
        f"SUDHEER'S STORY ANGLE:\n{p.get('story', '')[:400]}\n\n"
        f"PREFERENCES:\n{p.get('preferences', '')[:400]}\n\n"
        f"PERSON TO SCORE:\n"
        f"Name: {person.get('name', '')}\n"
        f"Title: {person.get('title', '')}\n"
        f"Headline: {person.get('headline', '')}\n"
        f"Degree: {person.get('connection_degree', '3rd')}\n"
        f"Mutuals: {person.get('mutual_connections', 0)}\n"
        f"Summary: {person.get('summary', '')[:300]}\n"
        f"Recent activity: {person.get('recent_activity', 'none')}"
    )
    try:
        result = ask_json(prompt, system=inject_skill_as_system("score_contact"))
    except ValueError:
        from backend.agents.failure_handler import with_retry
        _score_log.warning(f'JSON parse error on first attempt — retrying for {person.get("name","?")}')
        result = with_retry(
            lambda: ask_json(prompt, system=inject_skill_as_system("score_contact")),
            failure_type="claude_json_parse_error",
            agent=None, ctx=ctx
        )
        if result is None:
            _score_log.error(f'Claude scoring failed entirely for {person.get("name","?")} — using score=0 fallback')
            log_agent_action('message_agent', job_id, session_id,
                             'message_agent.score_contact → SCORE_FAILED',
                             f'Claude parse failed for {person.get("name","?")}', 'FAILED')
            result = {"score": 0, "reason": "Claude parsing failed", "fit_angle": "",
                      "hook_source": "role_signal", "surface": False}
    result = validate_step(result, "score")

    _score_log.info(f'Score result: {result.get("score",0)}/10 | fit={result.get("fit_angle","?")} '
                    f'| hook={result.get("hook_source","?")} | surface={result.get("surface",False)} '
                    f'| reason: {result.get("reason","?")}')
    log_agent_action('message_agent', job_id, session_id,
                     'message_agent.score_contact → SCORE_RESULT',
                     f'score={result.get("score",0)}/10 fit={result.get("fit_angle","?")} '
                     f'hook={result.get("hook_source","?")} surface={result.get("surface",False)} | {result.get("reason","")}')
    return result


FIXED_CLOSE = "Curious how vibe coding and AI-native workflows will change our industry - would love to hear your take and riff on this a bit."
# 127 chars fixed close — body budget is computed per-name in draft_message()

MESSAGE_TEMPLATE = "Hey {first_name},\n{line_2}\n{line_3}\n" + FIXED_CLOSE


def draft_message(ctx: dict) -> dict:
    person = ctx["current_person"]
    score = ctx["current_score"]
    job_id = ctx.get("session", {}).get("job_id", 0)
    session_id = ctx.get("session", {}).get("session_id", 0)

    _draft_log = logging.getLogger('message_agent.draft_message')
    _draft_log.info(f'Drafting hook for {person.get("name","?")} ({person.get("title","?")})')
    log_agent_action('message_agent', job_id, session_id,
                     'message_agent.draft_message → DRAFTING',
                     f'{person.get("name","?")} | score={score.get("score",0)}')

    # Gather hook context
    hook_hints = []
    if has_observation(ctx, "RECENT_ACTIVITY"):
        notes = get_observations_by_category(ctx, "RECENT_ACTIVITY")
        if notes:
            hook_hints.append(f"recent activity: {notes[0]}")
    if has_observation(ctx, "HOOK_CANDIDATE"):
        notes = get_observations_by_category(ctx, "HOOK_CANDIDATE")
        if notes:
            hook_hints.append(f"specific hook: {notes[0]}")
    if has_observation(ctx, "AI_SIGNAL"):
        hook_hints.append("AI/automation in their profile — good tension angle")
    if has_observation(ctx, "MUTUAL_CONNECTION"):
        hook_hints.append("mutual connection exists")

    first_name = (person.get('name', 'there') or 'there').split()[0]
    # Dynamic budget: 300 total - "Hey {name},\n" - 2 more newlines - fixed close
    body_budget = 300 - (len(first_name) + 6) - 2 - len(FIXED_CLOSE)

    prompt = (
        f"PERSON:\n"
        f"Name: {person.get('name', '')}\n"
        f"Title: {person.get('title', '')}\n"
        f"Headline: {person.get('headline', '')}\n"
        f"Company: {person.get('company', '')}\n"
        f"Recent activity: {person.get('recent_activity', 'none')}\n\n"
        f"WHY CHOSEN: {score.get('reason', '')}\n"
        f"FIT ANGLE: {score.get('fit_angle', '')}\n\n"
        f"CONTEXT:\n{chr(10).join(hook_hints) if hook_hints else 'none — use role or company signal'}\n\n"
        f"HARD BUDGET: line_2 + line_3 combined must be ≤ {body_budget} chars.\n"
        f"Aim for line_2 ≤ 85 chars, line_3 ≤ 60 chars.\n"
        f"Return JSON: line_2, line_3, hook_source, applied_preferences"
    )

    system = inject_skill_as_system("draft_message")

    try:
        result = ask_json(prompt, system=system)
    except ValueError:
        from backend.agents.failure_handler import with_retry
        result = with_retry(
            lambda: ask_json(prompt, system=system),
            failure_type="claude_json_parse_error",
            agent=None, ctx=ctx
        )
        if result is None:
            result = {}

    line_2 = (result.get("line_2") or "").strip()
    line_3 = (result.get("line_3") or "").strip()

    # Fallbacks if Claude returns nothing
    if not line_2:
        line_2 = f"Been following your work on AI in product - the gap between hype and actual workflow change is real."
    if not line_3:
        line_3 = f"Your work at {person.get('company', 'your company')} sits right at that intersection."

    # Hard-trim combined body to actual budget for this person
    body = line_2 + "\n" + line_3
    if len(body) > body_budget:
        # trim line_3 first, then line_2 if still over
        over = len(body) - body_budget
        line_3 = line_3[:max(10, len(line_3) - over)].rsplit(' ', 1)[0]
        body = line_2 + "\n" + line_3
        if len(body) > body_budget:
            over2 = len(body) - body_budget
            line_2 = line_2[:max(20, len(line_2) - over2)].rsplit(' ', 1)[0]

    draft_a = MESSAGE_TEMPLATE.format(first_name=first_name, line_2=line_2, line_3=line_3)

    _draft_log.info(f'Draft: {len(draft_a)} chars | line_2={line_2!r}')
    log_agent_action('message_agent', job_id, session_id,
                     'message_agent.draft_message → DRAFT_READY',
                     f'{len(draft_a)} chars | {line_2[:60]}')

    return {
        "draft_a": draft_a,
        "draft_b": "",
        "recommended": "A",
        "hook_source": result.get("hook_source", "role_signal"),
        "char_count_a": len(draft_a),
        "char_count_b": 0,
        "applied_preferences": result.get("applied_preferences", []),
        "drift_detected": False,
        "violations_found": [],
    }
