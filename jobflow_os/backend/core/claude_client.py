import json
import anthropic
from backend.config import cfg

client = anthropic.Anthropic(api_key=cfg['claude']['api_key'])


def ask(prompt: str, system: str = None, max_tokens: int = None) -> str:
    kwargs = {
        'model': cfg['claude']['model'],
        'max_tokens': max_tokens or cfg['claude']['max_tokens'],
        'messages': [{'role': 'user', 'content': prompt}],
    }
    if system:
        kwargs['system'] = system
    message = client.messages.create(**kwargs)
    return message.content[0].text


def ask_json(prompt: str, system: str = None) -> dict:
    json_instruction = 'Return only valid JSON. No markdown. No explanation.'
    if system:
        combined_system = system.rstrip() + '\n' + json_instruction
    else:
        combined_system = json_instruction

    response = ask(prompt, system=combined_system, max_tokens=cfg['claude']['max_tokens'])

    # Strip ```json and ``` fences if present
    cleaned = response.strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.split('\n', 1)[-1]
        if cleaned.endswith('```'):
            cleaned = cleaned.rsplit('```', 1)[0]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"claude_json_parse_error: {str(e)} | raw: {cleaned[:200]}")
