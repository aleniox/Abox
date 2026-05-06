"""
Discord bot event handlers
"""
import discord
from discord.ext import commands
import logging
import asyncio
import os
from pathlib import Path

import modules.config as config
import modules.core.agent_chat as agent_chat
import bots.upload_media as upload_media
import modules.tools.tool_others as tool_others
import modules.core.voice_clone as text2speech
from bot_config import VOICE_CACHE_PATH

logger = logging.getLogger(__name__)
connection_retries = 0
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds


def setup_events(bot: commands.Bot, max_retries: int = 5, retry_delay: int = 5):
    """Register event handlers with the bot"""
    global connection_retries, MAX_RETRIES, RETRY_DELAY
    
    MAX_RETRIES = max_retries
    RETRY_DELAY = retry_delay

    @bot.event
    async def on_ready():
        """Log when bot is ready"""
        global connection_retries
        connection_retries = 0
        logger.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
        logger.info(f"Connected to {len(bot.guilds)} guild(s)")
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name="your requests")
        )

    @bot.event
    async def on_disconnect():
        """Log when bot disconnects"""
        logger.warning("Bot has disconnected from Discord!")

    @bot.event
    async def on_resumed():
        """Log when bot resumes connection"""
        logger.info("Bot has reconnected to Discord!")

    @bot.event
    async def on_message(message):
        """Handle incoming messages"""
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
                # Handle voice messages
                elif attachment.content_type and attachment.content_type.startswith("audio/"):
                    file_path = await upload_media.save_audio(attachment, download_folder)
                    if file_path:
                        audio_paths.append(file_path)
            except Exception as e:
                logger.error(f"Error processing attachment: {e}")
                await message.channel.send("⚠️ Có lỗi khi xử lý tệp đính kèm.")

        # Process message with content or attachments
        if message.content or image_paths or audio_paths:
            async with message.channel.typing():
                loop = asyncio.get_running_loop()
                try:
                    if image_paths:
                        image_urls = [att.url for att in message.attachments if att.content_type.startswith("image/")]
                        await message.channel.send(
                            f"📷 Nhận được {len(image_urls)} ảnh của {message.author.display_name}: {', '.join(image_urls)}"
                        )
                    
                    if audio_paths:
                        await message.channel.send(
                            f"🎤 Nhận được {len(audio_paths)} tin nhắn thoại của {message.author.display_name}."
                        )
                    
                    # Call LLM with text and/or images
                    response = await loop.run_in_executor(
                        None,
                        agent_chat.chat,
                        message.content or "",
                        image_paths,
                        audio_paths
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    if "Failed to connect to Ollama" in str(e):
                        try:
                            # Retry after restarting Ollama
                            response = await loop.run_in_executor(
                                None,
                                agent_chat.chat,
                                message.content or "",
                                image_paths,
                                audio_paths
                            )
                        except Exception as retry_error:
                            logger.error(f"Retry failed: {retry_error}")
                            response = "⚠️ Có lỗi nghiêm trọng xảy ra khi xử lý yêu cầu."
                    else:
                        response = "⚠️ Có lỗi xảy ra khi xử lý yêu cầu."
                        
                # Handle image responses
                if isinstance(response, dict):
                    await message.channel.send(file=discord.File(response.get('images', None)))
                    return
                
                response = tool_others.format_discord_message(response)
                
                # Send voice response if user sent audio
                if audio_paths:
                    voice_file = VOICE_CACHE_PATH.format(message.id)
                    await asyncio.to_thread(
                        text2speech.run, 
                        voice_file,
                        response
                    )
                    if os.path.exists(voice_file):
                        await message.channel.send(response, file=discord.File(voice_file))
                    else:
                        await message.channel.send(response)
                else:
                    await message.channel.send(response)


def get_run_bot_func(bot: commands.Bot, token: str, max_retries: int = 5, retry_delay: int = 5):
    """Get the run_bot function with proper configuration"""
    global connection_retries, MAX_RETRIES, RETRY_DELAY
    
    MAX_RETRIES = max_retries
    RETRY_DELAY = retry_delay

    async def run_bot():
        """Run the bot with reconnection logic"""
        global connection_retries
        
        while True:
            try:
                logger.info(f"Attempting to connect to Discord (attempt {connection_retries + 1}/{MAX_RETRIES})")
                await bot.start(token)
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

    return run_bot
