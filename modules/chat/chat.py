# Chat module - Simple chat functionality
import logging
from typing import List, Dict
from pathlib import Path
import modules.memory.memory as memory
import modules.config.config as config
import modules.core.call_api_llm as call_api_llm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger("chat")

# Model configuration
MODEL_NAME = config.MODEL_NAME

# Load personality prompt from file
PERSONALITY_PROMPT_FILE = Path(__file__).parent.parent.parent / "storage" / "prompts" / "personality_prompt.md"

def load_prompt_system() -> str:
    """Load personality prompt from file"""
    if PERSONALITY_PROMPT_FILE.exists():
        try:
            with open(PERSONALITY_PROMPT_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"⚠️ Lỗi khi đọc personality prompt: {e}")
            return "You are a helpful AI assistant."
    else:
        logger.warning(f"⚠️ File personality prompt không tìm thấy: {PERSONALITY_PROMPT_FILE}")
        return "You are a helpful AI assistant."

prompt_system = load_prompt_system()

# Initialize chat history
HISTORY_CHAT: List[Dict[str, str]] = [
    {"role": "system", "content": prompt_system}
]

# Load existing chat history
LOAD_HISTORY = memory.load_chat_history()
HISTORY_CHAT = LOAD_HISTORY + HISTORY_CHAT


def chat(message: str, image_paths: List = None, audio_paths: List = None) -> str:
    """
    Send a message and get a response from the chatbot
    
    Args:
        message: User message text
        image_paths: Optional list of image paths (not used in simple chat mode)
        audio_paths: Optional list of audio paths (not used in simple chat mode)
        
    Returns:
        Assistant response text
    """
    global HISTORY_CHAT, MODEL_NAME
    
    if not message or not message.strip():
        return "⚠️ Vui lòng nhập tin nhắn."
    
    logger.info(f"📝 User: {message}")
    
    # Create user message
    user_message = {"role": "user", "content": message.strip()}
    HISTORY_CHAT.append(user_message)
    
    # Call LLM API
    try:
        response_data = call_api_llm.call_chat_api(
            model=MODEL_NAME,
            messages=HISTORY_CHAT,
            stream=False
        )
        
        response_json = response_data.json()
        
        # Extract response based on API format
        if "message" in response_json:
            response = response_json.get("message", {}).get("content", "")
        elif "choices" in response_json:
            response = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            response = "⚠️ Không thể lấy phản hồi từ API."
            logger.error(f"Unexpected API response format: {response_json}")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi gọi API: {e}")
        return f"❌ Lỗi: {str(e)}"
    
    # Save assistant response
    if response:
        response = response.strip()
        assistant_message = {"role": "assistant", "content": response}
        HISTORY_CHAT.append(assistant_message)
        
        # Save chat history
        memory.save_chat_history(HISTORY_CHAT[1:])
        logger.info(f"💬 Assistant: {response[:100]}...")
    
    return response


if __name__ == "__main__":
    logger.info(f"🤖 Chat started with model: {MODEL_NAME}")
    print("Type 'exit' or 'quit' to quit.\n")
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ["exit", "quit"]:
            logger.info("🛑 Chat ended.")
            break
        
        if not user_input:
            continue
        
        response = chat(user_input)
        print(f"\nAssistant: {response}\n")
