import os
DOWNLOAD_FOLDER = "downloads"
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}

MODEL_NAME = "gemma3:4b-it-qat"

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)