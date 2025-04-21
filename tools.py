import re

def format_discord_message(text):
    # Tìm toàn bộ các đoạn hành động $$...$$ và lời nói "..." hoặc văn bản thường
    # Regex sẽ giữ lại dấu để phân biệt
    pattern = r'\$\$(.*?)\$\$|"(.*?)"|([^\$"]+)'  # match $$...$$, "..." và phần còn lại

    matches = re.findall(pattern, text)
    result = ""

    for match in matches:
        action, quoted, normal = match

        if action:
            result += f"_ {action.strip()} _\n"
        elif quoted:
            result += f"```fix\n{quoted.strip()}\n```\n"
        elif normal and normal.strip():
            result += f"```fix\n{normal.strip()}\n```\n"

    return result.strip()
