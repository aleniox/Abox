import subprocess
import time
import os
import ollama

# --- Cấu hình ---
model_name = "gemma3:4b"
MAX_HISTORY_TURNS = 50  # Mỗi turn = 1 user + 1 bot => giữ 20 message + system

# --- System Prompt ---
try:
    import prompt
    system_prompt_content = prompt.prompt_system
except ImportError:
    print("Warning: 'prompt.py' not found. Using a default system prompt.")
    system_prompt_content = "You are a helpful AI assistant that can analyze images."

# Sử dụng model đa phương thức mà bạn đã pull
# Ví dụ: 'llava' hoặc 'llama3.2-vision' (đảm bảo model này có trên Ollama của bạn)
# LLava là model multimodal phổ biến và ổn định với Ollama hiện tại.
# Nếu 'llama3.2-vision' không hoạt động, thử 'llava'.
model_name = "gemma3:4b" # Hoặc "llama3.2-vision" nếu bạn chắc chắn nó hoạt động

# Lịch sử chat sẽ lưu các dictionaries theo định dạng mà ollama.chat mong đợi
# Bắt đầu với system prompt
history_chat = [{'role': 'system', 'content': system_prompt_content}]

# --- Giới hạn lịch sử chat ---
def trim_history(history):
    system = history[:1]
    turns = history[1:]
    return system + turns[-MAX_HISTORY_TURNS*2:]  # mỗi turn = user + assistant

# --- Khởi động Ollama ---
def start_ollama_server():
    try:
        subprocess.Popen(["ollama", "serve"])
        print("🟢 Starting Ollama server...")
        time.sleep(5)
        subprocess.run(["ollama", "pull", model_name], check=True)
        print(f"✅ Model '{model_name}' is ready.")
    except Exception as e:
        print(f"❌ Ollama startup error: {e}")

# --- Hàm chat chính ---
def chat(message="", image_path=None) -> str:
    global history_chat

    user_message = {'role': 'user', 'content': message or ""}
    if image_path and os.path.isfile(image_path):
        user_message['images'] = [image_path]
        print(f"🖼️ Image sent: {image_path}")

    # Trim lịch sử nếu quá dài
    messages = trim_history(history_chat + [user_message])

    try:
        stream = ollama.chat(model=model_name, messages=messages, stream=True, options={"num_ctx": 4096, "max_tokens": 512})
        response = ""
        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                content = chunk['message']['content']
                print(content, end="", flush=True)
                response += content
        print()

        # Cập nhật lịch sử sau khi nhận phản hồi thành công
        history_chat += [user_message, {'role': 'assistant', 'content': response}]
        return response

    except Exception as e:
        return f"⚠️ Error: {e}"

# --- Dùng thử (CLI) ---
if __name__ == "__main__":
    start_ollama_server()
    print("\n--- Starting Direct Ollama Multimodal Chat ---")
    print(f"Using model: {model_name}")
    print("Type 'exit' or 'quit' to end the chat.")
    print("To send an image, type: image <path_to_image> [your text message]")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            print("--- Ending Chat ---")
            break

        image_path = "downloads/processed_image.png"
        text_message = user_input

        if user_input.lower().startswith("image "):
            parts = user_input.split(" ", 2)
            if len(parts) > 1:
                image_path = parts[1]
                text_message = parts[2] if len(parts) > 2 else ""
            else:
                print("Invalid format. Use: image <path_to_image> [your text]")
                continue

        bot_response = chat(message=text_message, image_path=image_path)
