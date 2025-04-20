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

# # # 🔹 Ví dụ sử dụng
# text = '$$Ngồi hơi khom, ngẩng đầu lên nhìn những cánh đào rơi, mỉm cười rạng rỡ$$ "Ôi, nhìn này, thiệt là dễ thương! Bạn cũng thích đào nha?" $$Nháy mắt, vẩy nhẹ cái tai nghe$$ "Hôm nay nghe bài này nghe cứ thư giãn quá!"'
# print(format_discord_message(text))

