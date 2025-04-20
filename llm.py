import subprocess
import time
import ollama
import prompt

model_name = "gemma3:4b"
history_chat = []

def start_ollama_server():
    try:
        subprocess.Popen(["ollama", "serve"])
        print("🚀 Ollama server started...")
        ollama.pull(model_name)
        time.sleep(3)  # Chờ server khởi động
    except Exception as e:
        print("❌ Không thể khởi động Ollama:", e)

def chat(message):
    try:
        print("💬 Gửi prompt:", message)
        system_prompt = [{'role': 'system', 'content': prompt.prompt_system}]
        history_chat.append({'role': 'user', 'content': message})
        full_prompt = system_prompt + history_chat

        stream = ollama.chat(
            model=model_name,
            messages=full_prompt,
            stream=True,
        )

        response = ""
        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                content = chunk['message']['content']
                print(content, end='', flush=True)
                response += content
            else:
                print("⚠️ Chunk không hợp lệ:", chunk)

        # Lưu vào lịch sử nếu muốn duy trì context
        history_chat.append({'role': 'assistant', 'content': response})
        return response

    except Exception as e:
        print(f"❌ Lỗi khi stream từ Ollama: {e}")
        return "⚠️ Bot không thể phản hồi lúc này."
