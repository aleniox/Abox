import discord
from discord.ext import commands
from discord.ui import Button, View

import os
import logging
import asyncio
from pathlib import Path

from dotenv import load_dotenv
import modules.tools as tools
import modules.tools.agent_tools as agent_tools
import modules.core.llm_chain as llm_chain
import modules.config as config
import modules.tools.upload_media as upload_media
from discord import Embed, Color


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
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

# Global variable to track connection status
connection_retries = 0
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds

@bot.event
async def on_ready():
    """Log when the bot is ready and reset connection retries."""
    global connection_retries
    connection_retries = 0
    logger.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guild(s)")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="your requests"))

@bot.command(name="info")
async def send_info(ctx):
    """Gửi tin nhắn embed đẹp mắt"""
    embed = Embed(
        title="🎉 Chào mừng đến với Hana Bot",
        description=f"Tôi là trợ lý ảo của {ctx.author.display_name} trên Discord!",
        color=Color.purple()
    )
    
    embed.set_thumbnail(url="https://image.cdn2.seaart.me/2025-05-03/d0b1a4de878c73a4afrg/41459208059d8a6591789e1751030de8_high.webp")
    embed.add_field(name="🤖 Tính năng", value="• Trò chuyện thông minh\n• Tìm kiếm thông tin\n• Giải trí", inline=False)
    # embed.add_field(name="📝 Lệnh", value="!menu - Hiển thị menu chính\n!help - Trợ giúp", inline=False)
    embed.set_footer(text="Hana Bot © 2025")
    
    await ctx.send(embed=embed)

@bot.event
async def on_disconnect():
    """Log when the bot disconnects."""
    logger.warning("Bot has disconnected from Discord!")

@bot.event
async def on_resumed():
    """Log when the bot resumes connection."""
    logger.info("Bot has reconnected to Discord!")

async def run_bot():
    """Run the bot with reconnection logic."""
    global connection_retries
    
    while True:
        try:
            logger.info(f"Attempting to connect to Discord (attempt {connection_retries + 1}/{MAX_RETRIES})")
            await bot.start(TOKEN)
        except discord.errors.ConnectionClosed as e:
            connection_retries += 1
            if connection_retries >= MAX_RETRIES:
                logger.error(f"Max reconnection attempts reached. Exiting...")
                raise
            
            wait_time = RETRY_DELAY * (2 ** (connection_retries - 1))  # Exponential backoff
            logger.warning(f"Connection closed. Retrying in {wait_time} seconds... Error: {e}")
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Unexpected error: {e}. Attempting to reconnect...")
            connection_retries += 1
            if connection_retries >= MAX_RETRIES:
                logger.error(f"Max reconnection attempts reached. Exiting...")
                raise
            await asyncio.sleep(RETRY_DELAY)
        else:
            # Clean exit
            break

@bot.command(name="hana")
async def hana(ctx, *, query):
    """Search YouTube for videos."""
    videos = agent_tools.search_youtube(query)
    view = View()
    
    for idx, video in enumerate(videos[:5]):  # Limit to 5 buttons
        button = Button(
            label=f"{idx+1}. {video['title'][:50]}...",
            url=video['url'],  # YouTube link button
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
    logger.info(f"Processing message in session {session_id}")

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
        try:
            # Handle images
            if attachment.content_type and attachment.content_type.startswith("image/"):
                file_path = upload_media.save_image(attachment, download_folder)
                if file_path:
                    image_paths.append(file_path)
            # Handle voice messages (audio/ogg or audio/webm)
            elif attachment.content_type and attachment.content_type.startswith("audio/"):
                file_path = await upload_media.save_audio(attachment, download_folder)
                if file_path:
                    audio_paths.append(file_path)
        except Exception as e:
            logger.error(f"Error processing attachment: {e}")
            await message.channel.send("⚠️ Có lỗi khi xử lý tệp đính kèm.")

    # Send typing indicator and process message
    if message.content or image_paths or audio_paths:
        async with message.channel.typing():
            loop = asyncio.get_running_loop()
            try:
                if image_paths:
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
                    image_paths,
                    audio_paths
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                if "Failed to connect to Ollama" in str(e):
                    try:
                        llm_chain.start_ollama_server()
                        # Retry after restarting Ollama
                        response = await loop.run_in_executor(
                            None,
                            llm_chain.chat,
                            session_id,
                            message.content or "",
                            image_paths,
                            audio_paths
                        )
                    except Exception as retry_error:
                        logger.error(f"Retry failed: {retry_error}")
                        response = "⚠️ Có lỗi nghiêm trọng xảy ra khi xử lý yêu cầu."
                else:
                    response = "⚠️ Có lỗi xảy ra khi xử lý yêu cầu."
            
            response = tools.format_discord_message(response)
            await message.channel.send(response)