import re

def format_discord_message(text):
    # Tìm toàn bộ các đoạn (hành động trong ngoặc) và những đoạn còn lại
    pattern = r'\(.*?\)|[^()]+'
    parts = re.findall(pattern, text)

    result = ""

    for part in parts:
        part = part.strip()

        if not part:
            continue

        # Hành động
        if part.startswith("(") and part.endswith(")"):
            action = part[1:-1].strip()
            result += f"_ {action} _\n"
        else:
            result += f"```fix\n{part}\n```\n"

    return result.strip()

# # 🔹 Ví dụ sử dụng
# text = '''Ôi, trời ơi, hôm nay nắng đẹp quá! Mà hình như mình lại thấy mình đẹp hơn một chút nữa ấy nhỉ? (Nháy mắt, cười khúc khích) Thật ra mình chỉ đang nghĩ về bài hát mình đang nghe... nó cứ nguyen vọng quá!'''

# print(format_discord_message(text))
