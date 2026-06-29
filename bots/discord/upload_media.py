import discord
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import requests
from PIL import Image
from io import BytesIO

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("audio_logger")

async def save_audio(attachment: discord.Attachment, download_folder: Path) -> Optional[Path]:
    """Download and save a voice message attachment, returning the file path."""
    if not attachment.content_type or not attachment.content_type.startswith("audio/"):
        logger.debug(f"Skipping non-audio attachment: {attachment.filename}")
        return None

    try:
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        file_ext = "ogg"  # Discord voice messages are typically OGG files
        file_name = f"voice_{timestamp}_{attachment.id}.{file_ext}"
        file_path = download_folder / file_name

        # Download audio
        await attachment.save(file_path)
        logger.info(f"Saved voice message: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to save audio {attachment.filename}: {e}")
        return None
    


def save_image(attachment: discord.Attachment, download_folder: Path) -> Optional[Path]:
    """Download and save an image attachment, returning the file path."""
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        logger.debug(f"Skipping non-image attachment: {attachment.filename}")
        return None

    try:
        # Generate unique filename using timestamp and attachment ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        file_ext = attachment.filename.split(".")[-1] if "." in attachment.filename else "png"
        file_name = f"image_{timestamp}_{attachment.id}.{file_ext}"
        file_path = download_folder / file_name

        # Download image
        with requests.get(attachment.url, stream=True) as response:
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            img.save(file_path, format=img.format or "PNG")
            logger.info(f"Saved image: {file_path}")
            return file_path
    except Exception as e:
        logger.error(f"Failed to save image {attachment.filename}: {e}")
        return None