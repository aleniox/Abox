import discord
from discord.ext import commands
import os
import logging
import asyncio
import requests
from PIL import Image
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
import tools
import llm_chain
import config

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOK")
if not TOKEN:
    logger.error("DISCORD_TOK not found in environment variables.")
    raise ValueError("DISCORD_TOK is required.")

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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

@bot.event
async def on_ready():
    """Log when the bot is ready."""
    logger.info(f"Bot logged in as {bot.user}")

@bot.command()
async def start(ctx):
    """Greet the user."""
    await ctx.send(f"👋 Xin chào {ctx.author.display_name}!")

@bot.event
async def on_message(message):
    """Handle incoming messages, including text and multiple image attachments."""
    if message.author == bot.user:
        return

    # Process commands
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # Ensure download folder exists
    download_folder = Path(config.DOWNLOAD_FOLDER)
    download_folder.mkdir(parents=True, exist_ok=True)

    # Process attachments
    image_paths = []
    for attachment in message.attachments:
        file_path = save_image(attachment, download_folder)
        if file_path:
            image_paths.append(file_path)

    # Send typing indicator and process message
    if message.content or image_paths:
        async with message.channel.typing():
            loop = asyncio.get_running_loop()
            try:
                if image_paths:
                    # Send confirmation for images
                    image_urls = [att.url for att in message.attachments if att.content_type.startswith("image/")]
                    await message.channel.send(f"📷 Nhận được {len(image_urls)} ảnh: {', '.join(image_urls)}")
                
                # Call LLM with text and/or image paths
                response = await loop.run_in_executor(
                    None,
                    llm_chain.chat,
                    message.content or "",
                    image_paths  # Pass list of image paths
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                response = "⚠️ Có lỗi xảy ra khi xử lý yêu cầu."
            
            response = tools.format_discord_message(response)
            await message.channel.send(response)

def main():
    """Start the bot."""
    logger.info("Starting Discord bot...")
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Failed to run bot: {e}")
        raise

if __name__ == "__main__":
    main()