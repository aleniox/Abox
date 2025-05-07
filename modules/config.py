import os
DOWNLOAD_FOLDER = "downloads"
DATA_FOLDER = "data/simple_memory"
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}
MODEL_NAME_G = "gemma3:12b-it-qat"
MODEL_NAME_T = "qwen3:8b"
# "gemma3:12b-it-qat"
CONFIG_CHARACTOR = r"bots\config\Hana.json"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

MEMORY_CHAT_PATH = os.path.join(DATA_FOLDER + "/history_chat.json")
    