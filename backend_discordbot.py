import discord
from discord.ext import commands
from discord.ui import Button, View

import os
import logging
import asyncio

from pathlib import Path

from dotenv import load_dotenv
import tools.tools as tools
import tools.agent_tools as agent_tools
import llm_chain
import config
import tools.upload_media as upload_media



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


@bot.event
async def on_ready():
    """Log when the bot is ready."""
    logger.info(f"Bot logged in as {bot.user}")

@bot.command()
async def start(ctx):
    """Greet the user."""
    await ctx.send(f"👋 Xin chào {ctx.author.display_name}!")

@bot.command()
async def hana(ctx, *, query):
    videos = agent_tools.search_youtube(query)
    view = View()
    
    for idx, video in enumerate(videos[:5]):  # Giới hạn 5 nút
        button = Button(
            label=f"{idx+1}. {video['title'][:50]}...",
            url=video['url'],  # Nút mở link YouTube
            style=discord.ButtonStyle.link
        )
        view.add_item(button)
    
    await ctx.send(f"🔍 Kết quả tìm kiếm: '{query}'", view=view)

@bot.event
async def on_message(message):
    """Handle incoming messages, including text and multiple image attachments."""
    if message.author == bot.user:
        return
    session_id = str(message.channel.id)
    # Process commands
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # Ensure download folder exists
    download_folder = Path(config.DOWNLOAD_FOLDER)
    download_folder.mkdir(parents=True, exist_ok=True)

    # Process attachments
    image_paths = []
    audio_paths = []
    for attachment in message.attachments:
        # Handle images
        if attachment.content_type and attachment.content_type.startswith("image/"):
            file_path = upload_media.save_image(attachment, download_folder)
            if file_path:
                image_paths.append(file_path)
        # Handle voice messages (audio/ogg or audio/webm)
        elif attachment.content_type and attachment.content_type.startswith("audio/"):
            file_path = await upload_media.save_audio(attachment, download_folder)  # Note: await here
            if file_path:
                audio_paths.append(file_path)

    # Send typing indicator and process message
    if message.content or image_paths or audio_paths:
        async with message.channel.typing():
            loop = asyncio.get_running_loop()
            try:
                if image_paths:
                    # Send confirmation for images
                    image_urls = [att.url for att in message.attachments if att.content_type.startswith("image/")]
                    await message.channel.send(f"📷 Nhận được {len(image_urls)} ảnh: {', '.join(image_urls)}")
                if audio_paths:
                    await message.channel.send(f"🎤 Nhận được {len(audio_paths)} tin nhắn thoại.")
                # Call LLM with text and/or image paths
                response = await loop.run_in_executor(
                    None,
                    llm_chain.chat,
                    session_id,
                    message.content or "",
                    image_paths,  # Pass list of image paths
                    audio_paths
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                response = "⚠️ Có lỗi xảy ra khi xử lý yêu cầu."
            
            response = tools.format_discord_message(response)
            await message.channel.send(response)

def main():
    """Start the bot."""
    llm_chain.start_ollama_server()
    logger.info("Starting Discord bot...")
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Failed to run bot: {e}")
        raise

if __name__ == "__main__":
    main()