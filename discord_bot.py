from modules.core import agent_chat

agent_chat.start_ollama_server()

print("Gõ 'exit' hoặc 'quit' để thoát.")
print("Để gửi ảnh: image <đường_dẫn_ảnh> [nội dung_tin_nhắn]")

while True:
    user_input = input("\nYou: ").strip()
    if user_input.lower() in ["exit", "quit"]:
        print("🛑 Kết thúc chat.")
        break

    image_path = None
    text = user_input

    if user_input.lower().startswith("image "):
        parts = user_input.split(" ", 2)
        if len(parts) > 1:
            image_path = parts[1]
            text = parts[2] if len(parts) > 2 else ""
        else:
            print("⚠️ Cú pháp sai. Dùng: image <đường_dẫn_ảnh> [tin nhắn]")
            continue

    bot_response = agent_chat.chat(session_id=12, message=text, image_path=image_path)
    print(f"\nAssistant: {bot_response}")