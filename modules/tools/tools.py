import re

def format_discord_message(text):
    parts = re.split(r'(\$\$.*?\$\$|\(.*?\))', text)
    
    result = []
    for part in parts:
        if not part.strip():
            continue
            
        # Nếu là hành động ($$...$$)
        if part.startswith('$$') and part.endswith('$$'):
            action = part[2:-2].strip()
            if action:
                result.append(f"_ {action} _")
        elif part.startswith('(') and part.endswith(')'):
            action = part[1:-1].strip()
            if action:
                result.append(f"_ {action} _")
        # Nếu là lời thoại thông thường
        else:
            dialog = part.strip()
            if dialog:
                result.append(f"**{dialog}**")
    output = "\n".join(result)
    if "$$" in output:
        output.replace("$$", " ")
    return output
