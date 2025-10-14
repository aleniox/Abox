import discord
from discord.ext import commands
# from discord.ui import Button, View

import os
import logging
import asyncio
import csv
from pathlib import Path

from dotenv import load_dotenv
import modules.tools.tool_others as tool_others
# import modules.tools.agent_tools as agent_tools
import modules.core.agent_chat as agent_chat
import modules.tools.tool_searchs as tool_searchs
import modules.tools.tool_login as tool_login
import modules.config as config
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

class InfoForm(discord.ui.Modal, title="Nhập Thông Tin"):

    url = discord.ui.TextInput(label="Nhập link chấm công", placeholder="Nhập url...")
    username = discord.ui.TextInput(label="Username", placeholder="Nhập số điện thoại hoặc email...", style=discord.TextStyle.short)
    password = discord.ui.TextInput(label="Password", placeholder="Nhập mật khẩu...", style=discord.TextStyle.short)
    
    # bio = discord.ui.TextInput(label="Giới thiệu bản thân", style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Phản hồi khi người dùng submit form
        with open("downloads/cache/login_info.csv", "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([self.url, self.username, self.password])
        await interaction.response.send_message(
            f"✅ Link chấm công, **{self.url}**!\n"
            f"Email: {self.username}\n"
            f"Password: {self.password}", ephemeral=True
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
        
@bot.command(name="ckin")
async def checkin_and_out(ctx, style: str = 'ls'):
    with open("downloads/cache/login_info.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    # print(rows)
    print(style)
    for row in rows:
        image_path = tool_login.login_and_click(host= row[0], username=row[1], password=row[2], style=style)
        await ctx.channel.send(file=discord.File(image_path))
    await ctx.channel.send("Đã chấm công xong thưa ngài")
# ============================================================
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


@bot.command(name="youtube")
async def youtube(ctx, *, query):
    """Tìm kiếm video YouTube với giao diện nhúng (embed)"""
    try:
        # Hiển thị thông báo đang tìm kiếm (cách mới)
        async with ctx.typing():
            # Lấy kết quả từ YouTube
            videos = tool_searchs.search_youtube(query)
            
            if not videos:
                embed = discord.Embed(
                    title="❌ Không tìm thấy kết quả",
                    description=f"Không có video nào phù hợp với từ khóa `{query}`",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
            
            # Tạo Embed chính
            embed = discord.Embed(
                title=f"🔍 Kết quả tìm kiếm: '{query}'",
                description="",
                color=discord.Color.fuchsia()
            )
            
            # Sử dụng avatar mặc định nếu người dùng không có
            avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            
            # embed.set_thumbnail(url="https://image.cdn2.seaart.me/2025-05-04/d0bf765e878c738jp670/d3e8a8d77a85c89141f08043869e5c08_high.webp")  # Ảnh thumbnail
            embed.set_footer(text=f"Yêu cầu bởi {ctx.author.display_name}", icon_url=avatar_url)
            
            # Tạo View với các nút bấm
            view = discord.ui.View()
            
            # Thêm thông tin video vào Embed và tạo nút
            for idx, video in enumerate(videos[:5]):
                embed.description += (
                    f"**{idx+1}. [{video['title'][:50]}...]({video['url']})**\n"
                    f"👀 {video.get('views', 'N/A')} | ⏱️ {video.get('duration', 'N/A')}\n\n"
                )
                
                button = discord.ui.Button(
                    label=f"Video {idx+1}",
                    style=discord.ButtonStyle.link,
                    url=video['url'],
                    emoji="▶️",
                    row=0
                )
                view.add_item(button)
            
            await ctx.send(embed=embed, view=view)
            
    except Exception as e:
        error_embed = discord.Embed(
            title="⚠️ Lỗi khi tìm kiếm",
            description=f"Đã xảy ra lỗi: {str(e)}",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)
        print(f"[LỖI] Trong lệnh hana: {type(e).__name__}: {e}")

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
                    agent_chat.chat,
                    # session_id,
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
                        # agent_chat.start_ollama_server()
                        # Retry after restarting Ollama
                        response = await loop.run_in_executor(
                            None,
                            agent_chat.chat,
                            # session_id,
                            message.content or "",
                            image_paths,
                            audio_paths
                        )
                    except Exception as retry_error:
                        logger.error(f"Retry failed: {retry_error}")
                        response = "⚠️ Có lỗi nghiêm trọng xảy ra khi xử lý yêu cầu."
                else:
                    response = "⚠️ Có lỗi xảy ra khi xử lý yêu cầu."
                    
            if isinstance(response, dict):
                await message.channel.send(file=discord.File(response.get('images', None)))
                return
            response = tool_others.format_discord_message(response)
            await message.channel.send(response)