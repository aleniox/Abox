import os

MODEL_NAME = "HANA"
DOWNLOAD_FOLDER = "storage/downloads"
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}
MAX_TOKEN_CHAT = 2048
LLM_API_CHAT = "http://localhost:8080/v1/chat/completions"
TOKENIZE = "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)