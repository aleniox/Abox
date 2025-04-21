import subprocess
import time
import os
import ollama
import logging
from typing import Optional, List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load system prompt
try:
    from prompt import prompt_system
except ImportError:
    logger.warning("prompt.py not found. Using default system prompt.")
    prompt_system = "You are a helpful AI assistant that can analyze images."

# Configuration
MODEL_NAME = "gemma3:4b"
HISTORY_CHAT: List[Dict[str, str]] = [{"role": "system", "content": prompt_system}]

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

    messages = HISTORY_CHAT + [user_message]
    try:
        stream = ollama.chat(model=MODEL_NAME, messages=messages, stream=True)
        response = ""
        for chunk in stream:
            if content := chunk.get("message", {}).get("content"):
                print(content, end="", flush=True)
                response += content
        print()

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
        if user_input.lower() in ["exit", "quit"]:
            logger.info("Ending chat.")
            break

        image_path = "downloads/processed_image.png"
        text = user_input
        if user_input.lower().startswith("image "):
            parts = user_input.split(" ", 2)
            image_path = parts[1] if len(parts) > 1 else image_path
            text = parts[2] if len(parts) > 2 else ""

        chat(text, image_path)