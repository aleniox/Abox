import json
import re


def format_discord_message(text):
    text = remove_think_content(text)
    text = re.sub(r'^```(?:json)?\s*\n?|```$', '', text.strip())

    # Try to parse as JSON (new format: action/expression/dialogue)
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "dialogue" in data:
            parts = []
            if data.get("action"):
                parts.append(f"_ {data['action'].strip()} _")
            if data.get("expression"):
                parts.append(f"*({data['expression'].strip()})*")
            if data.get("dialogue"):
                parts.append(f"**{data['dialogue'].strip()}**")
            return "\n".join(parts)
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback to old format ($$action$$, (action), and text)
    parts = re.split(r'(\$\$.*?\$\$|\(.*?\))', text)

    result = []
    for part in parts:
        if not part.strip():
            continue

        if part.startswith('$$') and part.endswith('$$'):
            action = part[2:-2].strip()
            if action:
                result.append(f"_ {action} _")
        elif part.startswith('(') and part.endswith(')'):
            action = part[1:-1].strip()
            if action:
                result.append(f"_ {action} _")
        else:
            dialog = part.strip()
            if dialog:
                result.append(f"**{dialog}**")
    output = "\n".join(result)
    output = output.replace("$$", " ")
    return output.strip()


def remove_think_content(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)