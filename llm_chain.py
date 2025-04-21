import subprocess
import time
import os
import ollama
import logging
from typing import Optional, List, Dict

<<<<<<< HEAD
# --- Cấu hình ---
model_name = "gemma3:4b"
MAX_HISTORY_TURNS = 50  # Mỗi turn = 1 user + 1 bot => giữ 20 message + system

# --- System Prompt ---
=======
# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load system prompt
>>>>>>> 21b3706759ea816f47bedd4ddb6cd4a32857ddb9
try:
    from prompt import prompt_system
except ImportError:
    logger.warning("prompt.py not found. Using default system prompt.")
    prompt_system = "You are a helpful AI assistant that can analyze images."

# Configuration
MODEL_NAME = "gemma3:4b"
HISTORY_CHAT: List[Dict[str, str]] = [{"role": "system", "content": prompt_system}]

<<<<<<< HEAD
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
=======
def start_ollama_server() -> None:
    """Start Ollama server and pull the specified model."""
    try:
        logger.info("Starting Ollama server...")
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)  # Wait for server to start

        logger.info(f"Pulling model: {MODEL_NAME}")
        subprocess.run(["ollama", "pull", MODEL_NAME], check=True, capture_output=True, text=True)
        logger.info(f"Model {MODEL_NAME} ready.")
        time.sleep(2)
    except FileNotFoundError:
        logger.error("Ollama not found. Install from https://ollama.com/download.")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to pull model {MODEL_NAME}: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error starting Ollama: {e}")
        raise

def chat(message: str = "", image_path: Optional[str] = None) -> str:
    """Interact with Ollama model, supporting text and image inputs."""
    global HISTORY_CHAT
    logger.info("Processing chat request...")

    user_message = {"role": "user", "content": message or ""}
    if image_path and os.path.exists(image_path):
        user_message["images"] = [image_path]
        logger.info(f"Sending image: {image_path}")
    elif image_path:
        logger.warning(f"Image not found: {image_path}")

    if not user_message["content"] and "images" not in user_message:
        logger.warning("No text or valid image provided.")
        return "⚠️ Please provide text or a valid image."
>>>>>>> 21b3706759ea816f47bedd4ddb6cd4a32857ddb9

    messages = HISTORY_CHAT + [user_message]
    try:
<<<<<<< HEAD
        stream = ollama.chat(model=model_name, messages=messages, stream=True, options={"num_ctx": 4096, "max_tokens": 512})
        response = ""
        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                content = chunk['message']['content']
=======
        stream = ollama.chat(model=MODEL_NAME, messages=messages, stream=True)
        response = ""
        for chunk in stream:
            if content := chunk.get("message", {}).get("content"):
>>>>>>> 21b3706759ea816f47bedd4ddb6cd4a32857ddb9
                print(content, end="", flush=True)
                response += content
        print()

<<<<<<< HEAD
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
=======
        HISTORY_CHAT.extend([user_message, {"role": "assistant", "content": response}])
        return response
    except ollama.ResponseError as e:
        logger.error(f"Ollama API error: {e}")
        return f"⚠️ Ollama error: {e}"
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return "⚠️ Unable to respond."

if __name__ == "__main__":
    start_ollama_server()
    logger.info(f"Starting chat with model: {MODEL_NAME}")
    print("Type 'exit' or 'quit' to end. Use 'image <path> [text]' for images.")

    while True:
        user_input = input("You: ").strip()
>>>>>>> 21b3706759ea816f47bedd4ddb6cd4a32857ddb9
        if user_input.lower() in ["exit", "quit"]:
            logger.info("Ending chat.")
            break

        image_path = "downloads/processed_image.png"
<<<<<<< HEAD
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
=======
        text = user_input
        if user_input.lower().startswith("image "):
            parts = user_input.split(" ", 2)
            image_path = parts[1] if len(parts) > 1 else image_path
            text = parts[2] if len(parts) > 2 else ""

        chat(text, image_path)
>>>>>>> 21b3706759ea816f47bedd4ddb6cd4a32857ddb9
