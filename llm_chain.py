import subprocess
import time
import os
import ollama
import logging
from typing import Optional, List, Dict

# --- Cấu hình logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Cấu hình model và prompt ---
MODEL_NAME = "gemma3:4b"
MAX_HISTORY_TURNS = 50  # Mỗi turn = user + assistant

try:
    from prompt import prompt_system
except ImportError:
    logger.warning("prompt.py not found. Using default system prompt.")
    prompt_system = "You are a helpful AI assistant that can analyze images."

# --- Lịch sử chat ---
HISTORY_CHAT: List[Dict[str, str]] = [{"role": "system", "content": prompt_system}]

def trim_history(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Giới hạn số lượt trò chuyện trong lịch sử."""
    system = history[:1]
    turns = history[1:]
    return system + turns[-MAX_HISTORY_TURNS * 2:]

def start_ollama_server() -> None:
    """Khởi động Ollama và pull model."""
    try:
        logger.info("Starting Ollama server...")
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)

        logger.info(f"Pulling model: {MODEL_NAME}")
        subprocess.run(["ollama", "pull", MODEL_NAME], check=True, capture_output=True, text=True)
        logger.info(f"✅ Model '{MODEL_NAME}' is ready.")
    except FileNotFoundError:
        logger.error("❌ Ollama không được tìm thấy. Cài đặt tại: https://ollama.com/download")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Không thể pull model {MODEL_NAME}: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"❌ Lỗi khởi động Ollama: {e}")
        raise

def chat(message: str = "", image_path: Optional[List[str]] = None) -> str:
    """Gửi tin nhắn tới model, hỗ trợ cả văn bản và nhiều hình ảnh."""
    global HISTORY_CHAT
    logger.info("🧠 Đang xử lý yêu cầu chat...")

    user_message = {"role": "user", "content": message or ""}

    # Xử lý danh sách ảnh nếu có
    valid_images = []
    if image_path:
        for img in image_path:
            if os.path.isfile(img):
                valid_images.append(img)
                logger.info(f"🖼️ Đã thêm ảnh: {img}")
            else:
                logger.warning(f"⚠️ Ảnh không tồn tại: {img}")
        if valid_images:
            user_message["images"] = valid_images

    # Nếu không có nội dung và cũng không có ảnh hợp lệ
    if not user_message["content"] and "images" not in user_message:
        return "⚠️ Vui lòng cung cấp văn bản hoặc ít nhất một ảnh hợp lệ."

    messages = trim_history(HISTORY_CHAT + [user_message])

    try:
        response = ""
        stream = ollama.chat(model=MODEL_NAME, messages=messages, stream=True)
        for chunk in stream:
            content = chunk.get("message", {}).get("content", "")
            if content:
                print(content, end="", flush=True)
                response += content
        print()

        # Cập nhật lịch sử chat
        HISTORY_CHAT.extend([user_message, {"role": "assistant", "content": response}])
        return response

    except ollama.ResponseError as e:
        logger.error(f"Ollama API error: {e}")
        return f"⚠️ Lỗi Ollama: {e}"
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return "⚠️ Không thể phản hồi."


# --- CLI ---
if __name__ == "__main__":
    start_ollama_server()
    logger.info(f"🤖 Chat bắt đầu với model: {MODEL_NAME}")
    print("Gõ 'exit' hoặc 'quit' để thoát.")
    print("Để gửi ảnh: image <đường_dẫn_ảnh> [nội dung_tin_nhắn]")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            logger.info("🛑 Kết thúc chat.")
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

        bot_response = chat(message=text, image_path=image_path)
        print(f"\nAssistant: {bot_response}")
