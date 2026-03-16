import logging

logger = logging.getLogger(__name__)

PROFILE_SCHEMA = {
    "name":                  (str,   "",     True),
    "title":                 (str,   "",     True),
    "company":               (str,   "",     False),
    "linkedin_url":          (str,   "",     True),
    "headline":              (str,   "",     False),
    "summary":               (str,   "",     False),
    "current_role_duration": (str,   None,   False),
    "past_roles":            (list,  [],     False),
    "mutual_connections":    (int,   0,      False),
    "connection_degree":     (str,   "3rd",  False),
    "recent_activity":       (str,   None,   False),
    "skills_visible":        (list,  [],     False),
    "load_failed":           (bool,  False,  False),
}

SCORE_SCHEMA = {
    "score":       (int,  0,             True),
    "reason":      (str,  "",            True),
    "fit_angle":   (str,  "",            True),
    "hook_source": (str,  "role_signal", False),
    "surface":     (bool, False,         True),
}

DRAFT_SCHEMA = {
    "draft_a":             (str,   "",      True),
    "draft_b":             (str,   "",      False),
    "recommended":         (str,   "A",     False),
    "hook_source":         (str,   "",      False),
    "char_count_a":        (int,   0,       False),
    "char_count_b":        (int,   0,       False),
    "applied_preferences": (list,  [],      False),
    "drift_detected":      (bool,  False,   False),
    "violations_found":    (list,  [],      False),
}

ENRICHMENT_SCHEMA = {
    "company_summary":       (str,  "Not found.", True),
    "team_info":             (str,  "Not found.", False),
    "tech_stack":            (list, [],           False),
    "role_signals":          (list, [],           True),
    "culture_signals":       (list, [],           False),
    "linkedin_company_url":  (str,  "not found",  False),
    "fit_indicators":        (list, [],           True),
    "contact_targets":       (list, [],           True),
    "enrichment_confidence": (str,  "LOW",        False),
}

STORY_SCHEMA = {
    "headline":       (str,  "",  True),
    "key_strengths":  (list, [],  True),
    "talking_points": (list, [],  True),
    "gap_framing":    (str,  "No significant gaps identified.", False),
    "outreach_tone":  (str,  "",  False),
}

SCHEMAS = {
    "profile":    PROFILE_SCHEMA,
    "score":      SCORE_SCHEMA,
    "draft":      DRAFT_SCHEMA,
    "enrichment": ENRICHMENT_SCHEMA,
    "story":      STORY_SCHEMA,
}


def validate(data: dict, schema: dict, step_name: str) -> dict:
    """Validates data against schema. Returns cleaned dict. Never raises."""
    result = dict(data)
    for field, (expected_type, default, required) in schema.items():
        value = result.get(field)

        # Handle None for basic types
        if value is None:
            if expected_type == list:
                value = []
            elif expected_type == str:
                value = "" if default == "" else default
            elif expected_type == int:
                value = 0 if default == 0 else default
            elif expected_type == bool:
                value = False

        # Type check
        if value is not None and not isinstance(value, expected_type):
            if required:
                logger.warning(f"[{step_name}] Field '{field}' wrong type — using default")
            result[field] = default if default is not None else (
                [] if expected_type == list else
                "" if expected_type == str else
                0 if expected_type == int else
                False
            )
        elif field not in result or result.get(field) is None:
            if required and field not in data:
                logger.warning(f"[{step_name}] Required field '{field}' missing — using default")
            result[field] = value if value is not None else default
        else:
            result[field] = value if value is not None else result[field]

    return result


def validate_step(data: dict, step: str) -> dict:
    """Convenience wrapper. step must be a key in SCHEMAS."""
    if step not in SCHEMAS:
        raise ValueError(f"Unknown step: {step}. Valid: {list(SCHEMAS.keys())}")
    return validate(data, SCHEMAS[step], step)
