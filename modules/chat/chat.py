import logging
import base64
from pathlib import Path
from typing import List, Dict, Optional

import modules.memory.memory as memory
import modules.config.config as config
import modules.core.call_api_llm as call_api_llm
import modules.agent.agent_tools as agent_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger("chat")

MODEL_NAME = config.MODEL_NAME
PERSONALITY_PROMPT_FILE = Path(__file__).parent.parent.parent / "storage" / "prompts" / "personality_prompt.md"


def load_prompt_system() -> str:
    if PERSONALITY_PROMPT_FILE.exists():
        try:
            with open(PERSONALITY_PROMPT_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Lỗi khi đọc personality prompt: {e}")
            return "You are a helpful AI assistant."
    else:
        logger.warning(f"File personality prompt không tìm thấy: {PERSONALITY_PROMPT_FILE}")
        return "You are a helpful AI assistant."


prompt_system = load_prompt_system()
HISTORY_CHAT: List[Dict[str, str]] = [
    {"role": "system", "content": prompt_system}
]

LOAD_HISTORY = memory.load_chat_history()
HISTORY_CHAT = LOAD_HISTORY + HISTORY_CHAT


def _encode_image(image_path: Path) -> Optional[str]:
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Lỗi encode ảnh {image_path}: {e}")
        return None


def _build_content_parts(text: str, image_paths: List[Path]) -> list:
    parts = [{"type": "text", "text": text or ""}]
    for img_path in image_paths:
        b64 = _encode_image(img_path)
        if b64:
            ext = Path(img_path).suffix.lstrip(".") or "png"
            parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/{ext};base64,{b64}"}
            })
    return parts


def chat(message: str, image_paths: Optional[List[Path]] = None, audio_paths: Optional[List[Path]] = None):
    global HISTORY_CHAT, MODEL_NAME

    if not message and not image_paths:
        return "Vui lòng nhập tin nhắn hoặc gửi ảnh."

    logger.info(f"User: {message} | ảnh: {len(image_paths or [])} | audio: {len(audio_paths or [])}")

    user_content = _build_content_parts(message.strip(), image_paths or [])
    user_message = {"role": "user", "content": user_content}
    HISTORY_CHAT.append(user_message)

    try:
        # Step 1: agent tool-calling decision
        agent_result, generated_image = agent_tools.smart_agent_decision(
            {"role": "user", "content": message.strip()}
        )
        # agent_result is a list: if tool called, [tool_context, original_user_msg]
        # if no tool, [original_user_msg]
        final_messages = HISTORY_CHAT[:-1] + agent_result + [user_message]

        # Step 2: call LLM with full context
        response_data = call_api_llm.call_chat_api(
            model=MODEL_NAME,
            messages=final_messages,
            stream=False
        )

        if "message" in response_data:
            response = response_data.get("message", {}).get("content", "")
        elif "choices" in response_data:
            response = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            response = "Không thể lấy phản hồi từ API."
            logger.error(f"Unexpected API response format: {response_data}")

    except Exception as e:
        logger.error(f"Lỗi khi gọi API: {e}")
        import traceback
        traceback.print_exc()
        return f"Lỗi: {str(e)}"

    if response:
        response = response.strip()
        assistant_message = {"role": "assistant", "content": response}
        HISTORY_CHAT.append(assistant_message)
        memory.save_chat_history(HISTORY_CHAT[1:])
        logger.info(f"Assistant: {response[:100]}...")

    if generated_image:
        return {"text": response, "images": generated_image}

    return response


if __name__ == "__main__":
    logger.info(f"Chat started with model: {MODEL_NAME}")
    print("Type 'exit' or 'quit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            break
        if not user_input:
            continue
        response = chat(user_input)
        print(f"\nAssistant: {response}\n")
