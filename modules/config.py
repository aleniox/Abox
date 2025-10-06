import os
DOWNLOAD_FOLDER = "downloads"
DATA_FOLDER = "data/simple_memory"
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}
MODEL_NAME_T = "gemma3:4b"
MODEL_NAME_G = "qwen3:4b-instruct-2507-q4_K_M"
MAX_TOKEN_CHAT = 2048
OLLAMA_API_URLCHAT = "http://192.168.1.222:8070/v1/chat/completions"
TOKENIZE = "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
MODEL_NAME_EMBED = ""
# "qwen3:1.7b"
# "gemma3:12b-it-qat"
CONFIG_CHARACTOR = r"bots\config\Hana.json"
# r"bots\config\Yumi.json"
# r"bots\config\Hana.json"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

MEMORY_CHAT_PATH = os.path.join(DATA_FOLDER + "/history_chat.json")
