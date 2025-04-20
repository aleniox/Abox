import subprocess
import time
import ollama
import prompt
import os

model_name = "llama3.2-vision"  # model hỗ trợ hình ảnh
history_chat = []

def start_ollama_server():
    try:
        subprocess.Popen(["ollama", "serve"])
        print("🚀 Ollama server started...")
        ollama.pull(model_name)
        time.sleep(3)
    except Exception as e:
        print("❌ Không thể khởi động Ollama:", e)

def chat(message, image_path=None):
    try:
        print("💬 Gửi prompt:", message)
        system_prompt = {'role': 'system', 'content': prompt.prompt_system}

        # Tạo message user
        user_msg = {
            'role': 'user',
            'content': message
        }

        # Nếu có ảnh, thêm vào message
        if image_path and os.path.exists(image_path):
            user_msg['images'] = [image_path]
            print(f"🖼️ Ảnh được gửi cùng: {image_path}")

        # Tổng hợp prompt
        messages = [system_prompt] + history_chat + [user_msg]

        # Gửi đến model
        stream = ollama.chat(
            model=model_name,
            messages=messages,
            stream=True,
        )

        # Xử lý phản hồi dạng stream
        response = ""
        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                content = chunk['message']['content']
                print(content, end='', flush=True)
                response += content
            else:
                print("⚠️ Chunk không hợp lệ:", chunk)

        # Lưu vào history
        history_chat.append(user_msg)
        history_chat.append({'role': 'assistant', 'content': response})

        return response

    except Exception as e:
        print(f"❌ Lỗi khi xử lý chat: {e}")
        return "⚠️ Bot không thể phản hồi lúc này."
