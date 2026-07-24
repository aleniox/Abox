import os
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "HANA"
DOWNLOAD_FOLDER = "storage/downloads"
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}
MAX_TOKEN_CHAT = 20480
LLM_API_CHAT = os.getenv("LLM_API_CHAT", "http://localhost:8080/v1/chat/completions")
ASR_API = os.getenv("ASR_API", "http://10.0.99.116:8000/transcribe")
TOKENIZE = "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
TAVILY_KEY = os.getenv("TAVILY_TOKEN", "")

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)