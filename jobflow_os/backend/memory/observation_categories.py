OBSERVATION_CATEGORIES = {
    "AI_SIGNAL":         "profile mentions AI, ML, automation, agents, or LLMs",
    "MUTUAL_CONNECTION": "has mutual connections with Sudheer",
    "RECENT_ACTIVITY":   "posted or commented on LinkedIn in last 30 days",
    "BUILDER_SIGNAL":    "profile shows they build things — engineer, technical PM, founder",
    "ENTERPRISE_SIGNAL": "has worked at enterprise-scale companies or products",
    "DATA_SIGNAL":       "profile touches data, analytics, pipelines, or BI",
    "STARTUP_SIGNAL":    "early-stage company, small team, fast-moving role",
    "SENIORITY_MATCH":   "title seniority matches what Sudheer should target",
    "TITLE_MISMATCH":    "title is adjacent but not ideal — note why still surfacing",
    "LOW_PROFILE":       "sparse profile — limited About, no activity, thin history",
    "HOOK_CANDIDATE":    "something specific enough to use as a message hook",
    "freeform":          "agent observed something that fits no fixed category",
}


def add_observation(ctx: dict, step: str, category: str, note: str) -> dict:
    """Adds one observation to ctx['observations']. Forces unknown categories to 'freeform'."""
    if category not in OBSERVATION_CATEGORIES:
        category = "freeform"
    ctx['observations'].append({'step': step, 'category': category, 'note': note})
    return ctx


def get_observations_by_category(ctx: dict, category: str) -> list:
    """Returns list of note strings matching a category."""
    return [
        obs['note'] for obs in ctx.get('observations', [])
        if obs.get('category') == category
    ]


def has_observation(ctx: dict, category: str) -> bool:
    """Returns True if at least one observation of this category exists."""
    return any(obs.get('category') == category for obs in ctx.get('observations', []))
