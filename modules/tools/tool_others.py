import json
import re


def format_discord_message(text):

    text = re.sub(r'^```(?:json)?\s*\n?|```$', '', text.strip())

    # Try to parse as JSON (new format: action/expression/dialogue)
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "dialogue" in data:
            parts = []
            if data.get("action"):
                parts.append(f"_ {data['action'].strip()} _")
            # if data.get("expression"):
            #     parts.append(f"*({data['expression'].strip()})*")
            if data.get("dialogue"):
                parts.append(f"**{data['dialogue'].strip()}**")
            return "\n".join(parts)
    except (json.JSONDecodeError, TypeError):
        pass
        return "Tôi đã bị lỗi"