# import subprocess
# import time
import os
import logging
import base64
from typing import Optional, List, Dict
import modules.memory as memory
import modules.core.speech2text as speech2text
import modules.tools.agent_tools as agent_tools
import modules.config as config
import modules.core.call_api_llm as call_api_llm
import json

# --- Cấu hình logging ---
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s", encoding="utf-8")
logger = logging.getLogger("llm_chain")

# --- Cấu hình model và prompt ---
MODEL_NAME = config.MODEL_NAME_G

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

try:
    # from telegram_.templates import prompt_system
    from modules.prompts import prompt_system
    # from modules.core.prompt import prompt_system
except ImportError:
    logger.warning("prompt.py not found. Using default system prompt.")
    prompt_system = "You are a helpful AI assistant that can analyze images."

# --- Lịch sử chat ---
# vector_history = memory.VectorHistory()
HISTORY_CHAT: List[Dict[str, str]] = [
    {"role": "system", "content": prompt_system}]
if os.path.exists(config.MEMORY_CHAT_PATH):
    with open(config.MEMORY_CHAT_PATH, "r", encoding="utf-8") as f:
        LOAD_HISTORY = json.load(f)
else:
    LOAD_HISTORY = []
HISTORY_CHAT = HISTORY_CHAT + LOAD_HISTORY
# print(HISTORY_CHAT)


# def start_ollama_server() -> None:
#     # """Khởi động Ollama và pull model."""
#     try:
#         logger.info("Starting Ollama server...")
#         subprocess.Popen(["ollama", "serve"],
#                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
#         time.sleep(1)

#         # logger.info(f"Pulling model: {MODEL_NAME}")
#         # subprocess.run(["ollama", "pull", MODEL_NAME], check=True, capture_output=True, text=True)
#         logger.info(f"Model '{MODEL_NAME}' is ready.")
#     except FileNotFoundError:
#         logger.error(
#             "❌ Ollama không được tìm thấy. Cài đặt tại: https://ollama.com/download")
#         raise
#     except subprocess.CalledProcessError as e:
#         logger.error(f"❌ Không thể pull model {MODEL_NAME}: {e.stderr}")
#         raise
#     except Exception as e:
#         logger.error(f"❌ Lỗi khởi động Ollama: {e}")
#         raise

def process_and_accumulate_stream(response_stream):
    full_response = ""
    for line in response_stream.iter_lines():
        print(line)
        try:
            # print(line[5:])
            if line:
                data = json.loads(line[5:].decode("utf-8"))
                content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                # print(content, end="")
                full_response += content
                yield full_response
        except Exception as e:
            # print(line)
            continue

def chat(message: str = "", image_path: Optional[List[str]] = None, audio_path: str = None) -> str:
    global HISTORY_CHAT, MODEL_NAME
    logger.info("🧠 Đang xử lý yêu cầu chat...")

    user_message = {"role": "user", "content": message or ""}
    # vector_history.add_message(session_id, user_message)
    print(f"🗨️ Tin nhắn: {user_message['content']}")
    # Xử lý danh sách ảnh nếu có
    has_images = False
    if image_path:
        # Nếu image_path là list thì dùng luôn, nếu là string thì bọc vào list
        images_to_process = image_path if isinstance(image_path, list) else [image_path]
        
        content_items = [{"type": "text", "text": message or ""}]
        
        for img in images_to_process:
            if os.path.isfile(img):
                base64_image = encode_image(img)
                content_items.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                })
                has_images = True
                logger.info(f"🖼️ Đã thêm và mã hóa ảnh: {img}")
            else:
                logger.warning(f"⚠️ Ảnh không tồn tại: {img}")
        
        if has_images:
            user_message["content"] = content_items
            
    elif audio_path:
        # Xử lý tin nhắn thoại nếu có
        text = speech2text.process_voice_message(audio_path)
        if text:
            user_message["content"] = text
            logger.info(
                f"🎤 Đã chuyển đổi tin nhắn thoại thành văn bản: {text}")
        else:
            logger.warning("⚠️ Không thể chuyển đổi tin nhắn thoại.")
            return "⚠️ Không thể chuyển đổi tin nhắn thoại."

    # Nếu không có nội dung và cũng không có ảnh hợp lệ
    # check if content is list (vision) or string
    content_is_empty = False
    if isinstance(user_message["content"], str):
        if not user_message["content"]:
            content_is_empty = True
    elif isinstance(user_message["content"], list):
        if len(user_message["content"]) == 0:
            content_is_empty = True
            
    if content_is_empty and not has_images:
        return "⚠️ Vui lòng cung cấp văn bản hoặc ít nhất một ảnh hợp lệ."

    agent_message = agent_tools.smart_agent_decision(user_message)
    # agent_message = [user_message]
    print(f"🗨️ Tin nhắn sau khi xử lý: {agent_message}")
    
    if isinstance(agent_message, str):
        return agent_message 
    
    # Ở đây chúng ta tạo danh sách messages để gửi LLM
    # Nếu là tin nhắn có hình ảnh (content là list), ta ưu tiên gửi trực tiếp
    # vì smart_agent_decision có thể chưa hỗ trợ tốt tool calling cho vision 100%
    
    if has_images:
        messages = [{"role": "system", "content": prompt_system}, user_message]
    else:
        # Nếu không có ảnh, dùng logic cũ (công cộng các bước tool call nếu có)
        messages = [agent_message[0], {"role": "system", "content": prompt_system}, agent_message[-1]]

    response = ""
    stream = call_api_llm.call_chat_api(model=MODEL_NAME, messages=messages,
                         stream=False, 
                        #  options={"num_ctx": 10000}
                         )
    print(stream.json())
    response = stream.json().get("message", {}).get("content", "") if "choices" not in stream.json() else stream.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    # for chunk in process_and_accumulate_stream(stream):
    #     # print(chunk)
    #     response = chunk
        # content = chunk.get("message", {}).get("content", "")
        # if content:
        #     print(content, end="", flush=True)
            # response += content
    print()
    # Cập nhật lịch sử chat
    # response = response.replace("<think>", "").replace("</think>", "")
    import modules.tools.tool_others as tool_others
    # response = tool_others.remove_think_content(response)
    assistant_message = {"role": "assistant", "content": response.strip()}
    # vector_history.add_message(session_id, assistant_message)
    HISTORY_CHAT.extend([user_message, assistant_message])
    with open(config.MEMORY_CHAT_PATH, "w", encoding="utf-8") as f:
        json.dump(HISTORY_CHAT[1:], f, ensure_ascii=False, indent=2)
    return response


# --- CLI ---
if __name__ == "__main__":
    # start_ollama_server()
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

        bot_response = chat(session_id=12, message=text, image_path=image_path)
        print(f"\nAssistant: {bot_response}")
