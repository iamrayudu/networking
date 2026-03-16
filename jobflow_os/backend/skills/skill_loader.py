from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

SKILL_MAP = {
    "search_query":          "backend/skills/ms_search_query.txt",
    "profile_extract":       "backend/skills/ms_profile_extract.txt",
    "score_contact":         "backend/skills/ms_score_contact.txt",
    "draft_message":         "backend/skills/ms_draft_message.txt",
    "enrichment_search":     "backend/skills/ms_enrichment_search.txt",
    "enrichment_synthesise": "backend/skills/ms_enrichment_synthesise.txt",
    "story_write":           "backend/skills/ms_story_write.txt",
    "preference_infer":      "backend/skills/ms_preference_infer.txt",
}

_cache = {}


def load_skill(skill_name: str) -> str:
    if skill_name in _cache:
        return _cache[skill_name]
    if skill_name not in SKILL_MAP:
        raise FileNotFoundError(f"Unknown skill: {skill_name}. Valid: {list(SKILL_MAP.keys())}")
    path = ROOT / SKILL_MAP[skill_name]
    if not path.exists():
        raise FileNotFoundError(f"Skill file not found: {path}")
    text = path.read_text()
    _cache[skill_name] = text
    return text


def inject_skill(skill_name: str, prompt: str) -> str:
    skill_text = load_skill(skill_name)
    return f"=== SKILL: {skill_name.upper()} ===\n{skill_text}\n=== END SKILL ===\n\n{prompt}"


def inject_skill_as_system(skill_name: str) -> str:
    return load_skill(skill_name)


def inject_skill_with_voice(skill_name: str, ctx: dict) -> str:
    from backend.memory.voice_anchor import prepend_voice_anchor
    skill_text = load_skill(skill_name)
    return prepend_voice_anchor(ctx, skill_text)
