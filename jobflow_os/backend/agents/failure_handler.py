import logging
import time

logger = logging.getLogger(__name__)

FAILURE_POLICY = {
    # LinkedIn / Chrome failures
    "captcha_detected": {
        "severity":  "CRITICAL",
        "action":    "STOP_ALL",
        "message":   "CAPTCHA detected. All agents paused to protect your account. "
                     "Resolve the CAPTCHA in Chrome, then resume from the dashboard.",
        "retry":     False,
    },
    "redirected_to_login": {
        "severity":  "HIGH",
        "action":    "PAUSE_AND_ASK",
        "message":   "LinkedIn logged me out. Please log back in to Chrome, then tell me to resume.",
        "retry":     False,
    },
    "zero_results": {
        "severity":  "MEDIUM",
        "action":    "ASK_AND_WAIT",
        "message":   "No results found with 2nd-degree filter for {company}. "
                     "Want me to try without the connection filter, or move on?",
        "retry":     True,
        "retry_action": "widen_search_filter",
    },
    "profile_not_found": {
        "severity":  "LOW",
        "action":    "SKIP",
        "message":   None,
        "retry":     False,
    },
    "profile_too_sparse": {
        "severity":  "LOW",
        "action":    "SKIP",
        "message":   None,
        "retry":     False,
    },
    "private_profile": {
        "severity":  "LOW",
        "action":    "SKIP",
        "message":   None,
        "retry":     False,
    },
    "already_connected": {
        "severity":  "LOW",
        "action":    "MARK_AND_SKIP",
        "message":   None,
        "retry":     False,
    },
    "invitation_pending": {
        "severity":  "LOW",
        "action":    "MARK_AND_SKIP",
        "message":   None,
        "retry":     False,
    },
    "connect_unavailable": {
        "severity":  "LOW",
        "action":    "SKIP",
        "message":   None,
        "retry":     False,
    },
    "page_not_ready": {
        "severity":  "LOW",
        "action":    "RETRY_ONCE",
        "message":   None,
        "retry":     True,
        "retry_action": "wait_and_reload",
    },
    # Claude API failures
    "claude_json_parse_error": {
        "severity":  "MEDIUM",
        "action":    "RETRY_ONCE",
        "message":   None,
        "retry":     True,
        "retry_action": "retry_claude_call",
    },
    "claude_api_error": {
        "severity":  "HIGH",
        "action":    "PAUSE_AND_ASK",
        "message":   "Claude API returned an error: {detail}. Pausing this agent.",
        "retry":     True,
        "retry_action": "retry_claude_call",
    },
    "claude_empty_response": {
        "severity":  "MEDIUM",
        "action":    "RETRY_ONCE",
        "message":   None,
        "retry":     True,
        "retry_action": "retry_claude_call",
    },
    # Data failures
    "missing_profile_file": {
        "severity":  "CRITICAL",
        "action":    "STOP_AGENT",
        "message":   "profile/master_profile.md not found. "
                     "Create your profile file before running agents.",
        "retry":     False,
    },
    "missing_enrichment": {
        "severity":  "HIGH",
        "action":    "STOP_AGENT",
        "message":   "No enrichment data found for {company} — {role}. "
                     "Run enrichment agent first.",
        "retry":     False,
    },
    "missing_story": {
        "severity":  "MEDIUM",
        "action":    "PAUSE_AND_ASK",
        "message":   "No story file found for {company} — {role}. "
                     "Want me to generate it now before continuing?",
        "retry":     False,
    },
    # Selenium failures
    "selenium_timeout": {
        "severity":  "MEDIUM",
        "action":    "RETRY_ONCE",
        "message":   None,
        "retry":     True,
        "retry_action": "wait_and_reload",
    },
    "selenium_element_not_found": {
        "severity":  "LOW",
        "action":    "SKIP",
        "message":   None,
        "retry":     False,
    },
    "selenium_crash": {
        "severity":  "CRITICAL",
        "action":    "STOP_AGENT",
        "message":   "Chrome crashed unexpectedly. Saved progress to checkpoint. "
                     "Restart this agent to resume.",
        "retry":     False,
    },
}


def handle_failure(failure_type: str, agent, ctx: dict, detail: str = "", **kwargs) -> dict:
    """
    Main failure handler. Returns {"action": str, "should_continue": bool, "ctx": dict}
    should_continue=True means caller continues to next step.
    should_continue=False means caller must check action and respond.
    """
    policy = FAILURE_POLICY.get(failure_type)
    if not policy:
        policy = {
            "severity": "HIGH",
            "action": "PAUSE_AND_ASK",
            "message": f"Unknown failure: {failure_type}. {detail}",
            "retry": False,
        }

    # Log to agent_log
    if agent is not None:
        try:
            agent.log("FAILURE", f"{failure_type}: {detail}", policy["severity"])
        except Exception:
            pass

    # Log to database
    try:
        from backend.memory.database import log_failure
        agent_id = agent.agent_id if agent and hasattr(agent, 'agent_id') else "unknown"
        job_id = ctx.get("session", {}).get("job_id", 0) if ctx else 0
        if job_id == 0 and ctx:
            job_id = ctx.get("permanent", {}).get("role", {}).get("id", 0)
        session_id = ctx.get("session", {}).get("session_id", 0) if ctx else 0
        log_failure(
            agent_id=agent_id,
            job_id=job_id,
            session_id=session_id,
            failure_type=failure_type,
            severity=policy["severity"],
            action_taken=policy["action"],
            detail=detail,
        )
    except Exception:
        pass

    # Emit message if present
    msg_template = policy.get("message")
    if msg_template and agent is not None:
        try:
            message = msg_template.format(detail=detail, **kwargs)
            agent.emit("AGENT_MESSAGE", {"message": message})
        except Exception:
            pass

    action = policy["action"]
    ctx = ctx or {}

    if action == "SKIP":
        return {"action": "SKIP", "should_continue": True, "ctx": ctx}

    elif action == "MARK_AND_SKIP":
        linkedin_url = kwargs.get("linkedin_url", "")
        if linkedin_url and ctx:
            try:
                from backend.memory.context_object import mark_contacted
                ctx = mark_contacted(linkedin_url, ctx)
            except Exception:
                pass
        return {"action": "MARK_AND_SKIP", "should_continue": True, "ctx": ctx}

    elif action in ("RETRY_ONCE", "ASK_AND_WAIT"):
        return {"action": "RETRY", "should_continue": False, "ctx": ctx}

    elif action == "PAUSE_AND_ASK":
        if agent is not None:
            try:
                agent.pause_flag.set()
                agent.emit("AGENT_STATUS", {
                    "status": "waiting",
                    "current_action": "paused — failure"
                })
            except Exception:
                pass
        return {"action": "PAUSE", "should_continue": False, "ctx": ctx}

    elif action == "STOP_AGENT":
        if agent is not None:
            try:
                agent.stop_flag.set()
            except Exception:
                pass
        return {"action": "STOP", "should_continue": False, "ctx": ctx}

    elif action == "STOP_ALL":
        if agent is not None:
            try:
                agent.emit("ERROR", {"error_type": "CAPTCHA_DETECTED",
                                     "message": msg_template or "CAPTCHA detected",
                                     "recoverable": False})
                agent.stop_flag.set()
            except Exception:
                pass
        return {"action": "STOP_ALL", "should_continue": False, "ctx": ctx}

    return {"action": action, "should_continue": False, "ctx": ctx}


def with_retry(fn, failure_type: str, agent, ctx: dict,
               max_retries: int = 1, retry_delay: float = 3.0, **kwargs):
    """
    Wraps a callable with one retry on failure.
    Returns the function result, or None if all retries failed.
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                logger.warning(f"with_retry exhausted for {failure_type}: {e}")
                handle_failure(failure_type, agent, ctx, detail=str(e), **kwargs)
    return None
