ANCHOR_INTRO = "SUDHEER'S VOICE — READ THIS FIRST:"


def build_voice_anchor(ctx: dict) -> str:
    permanent = ctx.get('permanent', {})
    tone_guide = permanent.get('tone_guide', '')
    preferences = permanent.get('preferences', '')
    current_score = ctx.get('current_score', {})

    lines = [ANCHOR_INTRO]
    lines.append("He is a full-stack developer and AI/automation builder. Not a job seeker. A builder.")
    lines.append("He writes like he talks: direct, specific, no filler.")

    # Extract banned phrases from tone_guide
    banned = []
    in_never_say = False
    for line in tone_guide.split('\n'):
        if 'WHAT I NEVER SAY' in line.upper() or "what i never say" in line.lower() or "What I never say" in line:
            in_never_say = True
            continue
        if in_never_say:
            stripped = line.strip()
            if stripped.startswith('-'):
                phrase = stripped.lstrip('- ').strip()
                if phrase:
                    banned.append(phrase)
                if len(banned) >= 5:
                    break
            elif stripped.startswith('#') or stripped.startswith('##'):
                in_never_say = False

    if banned:
        lines.append(f"He never says: {', '.join(banned[:5])}")

    # Extract example sentence from tone_guide
    example_line = None
    in_example = False
    for line in tone_guide.split('\n'):
        if 'example of an opening' in line.lower():
            in_example = True
            continue
        if in_example:
            stripped = line.strip().strip('"')
            if stripped and not stripped.startswith('#'):
                example_line = stripped
                break
            elif stripped.startswith('#'):
                break

    if example_line:
        lines.append(f'He sounds like: "{example_line}"')

    # Add fit angle if set
    fit_angle = current_score.get('fit_angle')
    if fit_angle:
        lines.append(f"His current strongest angle: {fit_angle}")

    # Add top 3 preference rules
    pref_rules = []
    for line in preferences.split('\n'):
        stripped = line.strip()
        if stripped.startswith('-') and stripped:
            pref_rules.append(stripped)
            if len(pref_rules) >= 3:
                break

    if pref_rules:
        lines.append("Active preferences this session:")
        lines.extend(pref_rules[:3])

    anchor = '\n'.join(lines)

    # Trim if over 200 words
    words = anchor.split()
    if len(words) > 200:
        # Trim preferences to 2
        if pref_rules:
            lines_trimmed = [l for l in lines if l not in pref_rules[2:]]
            anchor = '\n'.join(lines_trimmed)
        words = anchor.split()
        if len(words) > 200:
            # Trim banned phrases to 3
            anchor_lines = anchor.split('\n')
            for i, l in enumerate(anchor_lines):
                if l.startswith("He never says:") and banned:
                    anchor_lines[i] = f"He never says: {', '.join(banned[:3])}"
                    break
            anchor = '\n'.join(anchor_lines)

    return anchor


def prepend_voice_anchor(ctx: dict, system_prompt: str) -> str:
    anchor = build_voice_anchor(ctx)
    return f"{anchor}\n\n{system_prompt}"
