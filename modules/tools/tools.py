import re

def format_discord_message(text):
    # Pattern để bắt các thành phần:
    # $$...$$ → Hành động (in nghiêng _..._)
    # Văn bản thường → Lời thoại (in đậm **...**)
    # Tách các phần hành động và lời thoại
    # parts = re.split(r'(\$\$.*?\$\$)', text)
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

# message = """
# (Hana đứng hình mất một giây, đôi mắt mở to hết cỡ. Tim đập thình thịch. Nụ cười của Hana tan biến, thay vào đó là sự ngập ngừng và bối rối)

# $$Hana nhắm mắt lại, đôi tay nắm chặt lấy tay cậu. Giọng nói nhỏ nhẹ, gần như thì thầm$$ Cậu... cậu thật sự muốn như vậy sao? (Hana mở mắt ra, nhìn cậu dò xét, ánh mắt tràn đầy sự bối rối nhưng cũng không kém phần mong đợi.)"""
# formatted = format_discord_message(message)
# print(formatted)