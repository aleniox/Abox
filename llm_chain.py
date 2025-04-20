import subprocess
import time
import os
# Không cần import các thư viện Langchain nữa
import ollama

# Assume 'prompt.py' contains a system prompt variable like:
# prompt_system = "You are a helpful AI assistant."
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


def start_ollama_server():
    """Starts the Ollama server and pulls the specified multimodal model."""
    try:
        print("🚀 Attempting to start Ollama server...")
        # Khởi động server. Lệnh này sẽ không làm gì nếu server đã chạy.
        subprocess.Popen(["ollama", "serve"])
        print("✅ Ollama server command issued. Waiting a few seconds...")
        time.sleep(5) # Đợi server khởi động

        print(f"🌐 Pulling multimodal model: {model_name}...")
        # Pull model
        process = subprocess.run(["ollama", "pull", model_name], check=True, capture_output=True, text=True)
        print(process.stdout)
        if process.stderr:
             # Pull command often prints progress to stderr
             print("Pull progress/info:\n", process.stderr)
        print(f"✨ Model {model_name} pulled successfully (or already exists).")
        time.sleep(3) # Đợi sau khi pull
    except FileNotFoundError:
         print("❌ Error: 'ollama' command not found. Is Ollama installed and in your PATH?")
         print("Please install Ollama from https://ollama.com/download")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error pulling model {model_name}: {e}")
        print(f"Please ensure the Ollama server is running and the model '{model_name}' is available or exists.")
        print(f"You might need to run 'ollama pull {model_name}' manually.")
    except Exception as e:
        print(f"❌ An unexpected error occurred trying to start Ollama or pull the model: {e}")


def chat(message: str = "", image_path: str = None) -> str:
    """
    Interacts with the Ollama model using the direct ollama library,
    supporting text and image input, and managing chat history.

    Args:
        message: The user's input text message (can be empty if only image is sent).
        image_path: Optional path to an image file.

    Returns:
        The model's response string.
    """
    global history_chat # Cần truy cập và sửa đổi biến global history_chat

    print("\n💬 Sending prompt to Ollama...")

    # Tạo message cho lượt chat hiện tại của người dùng
    current_user_message = {'role': 'user'}

    # Nội dung text
    if message:
        current_user_message['content'] = message
    else:
         # Nếu không có text, đặt content rỗng hoặc một placeholder
         current_user_message['content'] = ""

    # Input hình ảnh
    if image_path:
        if os.path.exists(image_path):
             # Thư viện ollama có thể nhận đường dẫn file ảnh trực tiếp trong parameter 'images'
            current_user_message['images'] = [image_path]
            if not message: # Nếu chỉ có ảnh mà không có text
                 print(f"🖼️ Sending image: {image_path}")
            else:
                 print(f"🖼️ Sending image: {image_path} with text.")
        else:
            print(f"❌ Error: Image file not found at {image_path}. Sending text only.")
            # Xóa khóa 'images' nếu đường dẫn không hợp lệ
            if 'images' in current_user_message:
                del current_user_message['images']


    # Kiểm tra xem có nội dung nào để gửi không
    if 'content' not in current_user_message and 'images' not in current_user_message:
         print("⚠️ No text or valid image provided.")
         return "⚠️ Please provide either text or a valid image."

    # Thêm message hiện tại của người dùng vào lịch sử chat cho lượt gọi API này
    # Lưu ý: Chúng ta thêm vào đây để gửi toàn bộ context lên Ollama,
    # bao gồm cả lượt user hiện tại. Sau khi nhận response, ta mới thêm
    # response của bot vào lịch sử để dùng cho các lượt sau.
    messages_for_ollama = history_chat + [current_user_message]


    try:
        # Gọi API chat của ollama với stream=True
        stream = ollama.chat(
            model=model_name,
            messages=messages_for_ollama, # Gửi toàn bộ lịch sử + message hiện tại
            stream=True,
        )

        response_text = ""
        print("🤖 Bot response:")
        # Xử lý stream response
        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                content = chunk['message']['content']
                print(content, end='', flush=True)
                response_text += content
            elif 'done' in chunk and chunk['done']:
                 # End of stream
                 pass
            else:
                 # Optional: print other chunk info for debugging
                 # print("⚠️ Other chunk data:", chunk)
                 pass

        print() # Xuống dòng sau khi in xong response

        # Chỉ thêm message của người dùng và response của bot vào lịch sử
        # sau khi nhận được response thành công.
        history_chat.append(current_user_message) # Thêm message user vừa gửi (có thể kèm ảnh)
        history_chat.append({'role': 'assistant', 'content': response_text}) # Thêm response của bot

        return response_text

    except ollama.ResponseError as e:
        print(f"\n❌ Ollama API error: {e}")
        # print(f"Details: {e.body}")
        return f"⚠️ Error communicating with Ollama: {e.message}"
    except Exception as e:
        print(f"\n❌ An unexpected error occurred during chat: {e}")
        return "⚠️ Bot cannot respond at this time."

# Example Usage:
if __name__ == "__main__":
    # Ensure the server is running and multimodal model is available
    start_ollama_server()

    print("\n--- Starting Direct Ollama Multimodal Chat ---")
    print(f"Using model: {model_name}")
    print("Type 'exit' or 'quit' to end the chat.")
    print("To send an image, type 'image <path_to_image> [your text message]'")
    print("Example: image ./my_photo.jpg What is in this picture?")
    print("Example: image ./diagram.png")
    print("\nNote: Ensure the image path is correct relative to where you run the script.")


    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("--- Ending Chat ---")
            break

        image_path = "downloads/processed_image.png"
        text_message = user_input

        # Check if the input starts with 'image '
        if user_input.lower().startswith("image "):
            parts = user_input.split(" ", 2) # Split into 'image', 'path', 'rest_of_text'
            if len(parts) > 1:
                image_path = parts[1]
                if len(parts) > 2:
                    text_message = parts[2]
                else:
                    text_message = "" # No text message provided, only image
            else:
                print("Invalid image command format. Use: image <path_to_image> [your text message]")
                continue # Ask for input again

        # Call the chat function with potential image path and text
        # The chat function handles cases where text_message might be empty if only image is sent
        bot_response = chat(message=text_message, image_path=image_path)
        # The response is already printed by the chat function during streaming