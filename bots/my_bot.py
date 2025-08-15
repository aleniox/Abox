import discord
from discord.ext import commands
from discord.ui import Button, View

import os
import csv
import logging
import asyncio
from pathlib import Path

from dotenv import load_dotenv
import modules.tools.tool_others as tool_others

# import modules.tools.agent_tools as agent_tools
# import modules.agent_chat as agent_chat
import modules.core.agent_chat as agent_chat
import modules.config as config
import modules.tools.tool_login as tool_login
import bots.upload_media as upload_media
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

MAX_DISCORD_MSG_LENGTH = 2000



# @bot.command(name="login")
# async def nhap_thong_tin(ctx):
#     def check(m):
#         return m.author == ctx.author and m.channel == ctx.channel

#     try:
#         await ctx.send("👤 Hãy nhập **số điện thoại hoặc email**:")
#         msg1 = await bot.wait_for("message", check=check, timeout=30)
#         username = msg1.content

#         await ctx.send("📝 Bây giờ hãy nhập **password** của bạn:")
#         msg2 = await bot.wait_for("message", check=check, timeout=60)
#         password = msg2.content

#         embed = discord.Embed(
#             title="✅ Đã nhận thông tin",
#             color=discord.Color.purple()
#         )
#         embed.add_field(name="👤 Số điện thoại hoặc email", value=username, inline=False)
#         embed.add_field(name="📝 Password", value=password, inline=False)
#         embed.set_footer(text=f"{bot.user.name} Bot © 2025")

#         await ctx.send(embed=embed)
#         with open("downloads/cache/login_info.csv", "a", encoding="utf-8", newline="") as f:
#             writer = csv.writer(f)
#             writer.writerow([ctx.author.name, username, password])
#     except asyncio.TimeoutError:
#         await ctx.send("⏰ Bạn không phản hồi kịp thời gian. Vui lòng thử lại lệnh `!form`.")

class InfoForm(discord.ui.Modal, title="Nhập Thông Tin"):

    url = discord.ui.TextInput(label="Nhập url", placeholder="Nhập url...")
    username = discord.ui.TextInput(label="Nhập email", placeholder="Nhập email...", style=discord.TextStyle.short)
    password = discord.ui.TextInput(label="Nhập password", placeholder="Nhập password...", style=discord.TextStyle.short)
    
    # password = discord.ui.TextInput(label="Nhập password", style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Phản hồi khi người dùng submit form
        with open("downloads/cache/login_info.csv", "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([self.url, self.username, self.password])
        await interaction.response.send_message(
            f"✅ Cảm ơn bạn, **{self.url}**!\n"
            f"Tuổi: {self.username}\n"
            f"Giới thiệu: {self.password}", ephemeral=True
        )

@bot.command()
async def form(ctx):
    """Lệnh gọi form nhập thông tin"""
    await ctx.send("📋 Bấm vào nút bên dưới để điền form:", view=FormView())

class FormView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Điền Form", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InfoForm())

@bot.command(name="checkin")
async def checkin_and_out(ctx, btn):
    with open("downloads/cache/login_info.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    print(rows)
    for row in rows:
        image_path = tool_login.login_and_click(username=row[1], password=row[2])
        await ctx.channel.send(file=discord.File(image_path))
    await ctx.channel.send("Đã chấm công xong thưa ngài")
    
async def send_long_message(channel, text):
    for i in range(0, len(text), MAX_DISCORD_MSG_LENGTH):
        part = text[i:i + MAX_DISCORD_MSG_LENGTH]
        await channel.send(part)

@bot.command(name="info")
async def send_info(ctx):
    """Gửi tin nhắn embed đẹp mắt"""
    embed = Embed(
        title=f"🎉 Chào mừng đến với {bot.user.name} Bot",
        description=f"Tôi là trợ lý ảo của {ctx.author.display_name} trên Discord!",
        color=Color.fuchsia()
    )
    
    embed.set_thumbnail(url="https://image.cdn2.seaart.me/2025-05-03/d0b1a4de878c73a4afrg/41459208059d8a6591789e1751030de8_high.webp")
    embed.add_field(name="🤖 Tính năng", value="• Trò chuyện thông minh\n• Tìm kiếm thông tin\n• Giải trí", inline=False)
    # embed.add_field(name="📝 Lệnh", value="!menu - Hiển thị menu chính\n!help - Trợ giúp", inline=False)
    embed.set_footer(text=f"{bot.user.name} Bot © 2025")
    
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    """Log when the bot is ready and reset connection retries."""
    global connection_retries
    connection_retries = 0
    logger.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guild(s)")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="your requests"))

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
                    await message.channel.send(f"📷 Nhận được {len(image_urls)} ảnh của {message.author.display_name}: {', '.join(image_urls)}")
                if audio_paths:
                    await message.channel.send(f"🎤 Nhận được {len(audio_paths)} tin nhắn thoại của {message.author.display_name}.")
                
                # Call LLM with text and/or image paths
                response = await loop.run_in_executor(
                    None,
                    agent_chat.chat_,
                    session_id,
                    message.content or "",
                    image_paths,
                    audio_paths
                )
                print(f"Response: {response}")
                if "images" in response:
                    for image_path in response["images"]:
                        await message.channel.send(file=discord.File(image_path))
                        return
            except Exception as e:
                logger.error(f"Error processing message: {e}")
            
            # response = tool_others.format_discord_message(response)
            response = tool_others.remove_think_content(response)
            # await message.channel.send(response)
            await send_long_message(message.channel, response)