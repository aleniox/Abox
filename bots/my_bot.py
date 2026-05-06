from discord.ext import tasks
import discord
from discord.ext import commands
from datetime import datetime, time as dt_time
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
import modules.core.voice_clone as text2speech
import bots.upload_media as upload_media
# from selenium.common.exceptions import WebDriverException, TimeoutException
from discord import Embed, Color
import pytz



VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOK")
USER_ID = int(os.getenv("USER_ID")) if os.getenv("USER_ID") else None
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
SETTIMER = 30

# Check-in Configuration
CHECKIN_CONFIG = {
    "MORNING_NOTIFY": dt_time(7, 30),
    "DEBUG_NOTIFY": dt_time(17, 31),
    "AFTERNOON_NOTIFY": dt_time(17, 31)
}
TASK_STYLE = "cc"  # Mặc định là 'ls'

scheduled_tasks = {}
last_sent_time = None  # Theo dõi (hour, minute) cuối cùng đã gửi thông báo


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
    async with ctx.channel.typing():
        rows = []
        
        # 1. Đọc tệp CSV (Bắt lỗi tệp)
        try:
            with open("downloads/cache/login_info.csv", "r", encoding="utf-8") as f:
                rows = list(csv.reader(f))
        except FileNotFoundError:
            await ctx.channel.send("❌ **Lỗi:** Không tìm thấy tệp `login_info.csv`.")
            return

        print(f"Bắt đầu chấm công, style: {style}")
        
        # 2. Lặp qua từng tài khoản (Bắt lỗi xử lý và Selenium)
        for i, row in enumerate(rows):
            host = row[0] if len(row) > 0 else "N/A"
            
            try:
                # Kiểm tra đủ 3 cột cơ bản
                if len(row) < 3:
                    await ctx.channel.send(f"⚠️ **Bỏ qua:** Dòng #{i+1} (`{host}`). Thiếu Host/User/Pass.")
                    continue
                    
                result = await asyncio.to_thread(
                    tool_login.login_and_click,
                    host=row[0], 
                    username=row[1], 
                    password=row[2], 
                    style=style
                )
                
                # Xử lý kết quả trả về (có thể là string đường dẫn ảnh hoặc dict chứa message)
                image_path = result
                msg_content = f"✅ Host `{host}`: **Thành công.**"
                
                if isinstance(result, dict):
                    image_path = result.get("screenshot")
                    if result.get("message"):
                        msg_content += f"\n{result['message']}"
                
                await ctx.channel.send(msg_content, file=discord.File(image_path))

            except Exception as e:
                # Lỗi chung
                import traceback
                traceback.print_exc()
                await ctx.channel.send(f"❌ Host `{host}`: **Lỗi chung.** Chi tiết: `{type(e).__name__}`")

    # 3. Kết thúc
    await ctx.channel.send("Đã hoàn tất quá trình chấm công.")

async def run_login_task():
    global last_sent_time
    print("Đã đến lúc chạy login_and_click()...")
    user = await bot.fetch_user(USER_ID)
    with open("downloads/cache/login_info.csv", "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    for i, row in enumerate(rows):
            host = row[0] if len(row) > 0 else "N/A"
            
            try:
                # Kiểm tra đủ 3 cột cơ bản
                if len(row) < 3:
                    await user.send(f"⚠️ **Bỏ qua:** Dòng #{i+1} (`{host}`). Thiếu Host/User/Pass.")
                    continue
                result = await asyncio.to_thread(
                    tool_login.login_and_click,
                    host=row[0], 
                    username=row[1], 
                    password=row[2], 
                    style=TASK_STYLE
                )
                
                # Xử lý kết quả trả về
                image_path = result
                msg_content = f"✅ Host `{host}`: **Thành công.**"
                
                if isinstance(result, dict):
                    image_path = result.get("screenshot")
                    if result.get("message"):
                        msg_content += f"\n{result['message']}"

                await user.send(msg_content, file=discord.File(image_path))
            except Exception as e:
                # Lỗi chung
                import traceback
                traceback.print_exc()
                await user.send(f"❌ Host `{host}`: **Lỗi chung.** Chi tiết: `{type(e).__name__}`")
    
    # Cập nhật last_sent_time để tránh gửi thông báo lại trong phút hiện tại
    now = datetime.now(VN_TZ)
    last_sent_time = (now.hour, now.minute)

class CancelAfternoonView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Hủy chấm công chiều", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
             await interaction.response.send_message("Bạn không có quyền.", ephemeral=True)
             return
        
        task = scheduled_tasks.get(self.user_id)
        if task:
            task.cancel()
            del scheduled_tasks[self.user_id]
            await interaction.response.send_message("✅ Đã hủy chấm công chiều.", ephemeral=True)
            # Delete the message containing the button
            try:
                await interaction.message.delete()
            except Exception:
                pass
        else:
            await interaction.response.send_message("⚠️ Không tìm thấy lịch chấm công chiều nào.", ephemeral=True)

# Task chạy mỗi phút, kiểm tra đến 05:30
@tasks.loop(minutes=1)
async def daily_task():
    global last_sent_time
    now = datetime.now(VN_TZ)
    now_time = now.time()
    current_time_tuple = (now_time.hour, now_time.minute)
    
    # Các khung giờ muốn gửi thông báo
    targets = [
        CHECKIN_CONFIG["MORNING_NOTIFY"], 
        CHECKIN_CONFIG["AFTERNOON_NOTIFY"], 
        CHECKIN_CONFIG["DEBUG_NOTIFY"]
    ]
    
    # Kiểm tra xem thời gian hiện tại có trùng bất kỳ khung giờ trong targets không
    if any(now_time.hour == t.hour and now_time.minute == t.minute for t in targets):
        # Nếu đã gửi thông báo cho giờ này rồi thì bỏ qua
        if last_sent_time == current_time_tuple:
            return
        
        # Cập nhật thời gian gửi
        last_sent_time = current_time_tuple
        try:
            # Send a DM with a button to trigger the task instead of running automatically
            user = await bot.fetch_user(USER_ID)
            class TimerModal(discord.ui.Modal, title="Đặt hẹn giờ"):
                minutes = discord.ui.TextInput(label="Số phút", placeholder="Nhập số phút (ví dụ: 30)", default="30")
                
                def __init__(self, view_instance):
                    super().__init__()
                    self.view_instance = view_instance

                async def on_submit(self, interaction: discord.Interaction):
                    try:
                        minutes_val = int(self.minutes.value)
                        if minutes_val <= 0:
                            raise ValueError
                    except ValueError:
                        await interaction.response.send_message("Vui lòng nhập một số nguyên dương hợp lệ.", ephemeral=True)
                        return

                    # Cancel existing timer if any
                    if self.view_instance.timer_task and not self.view_instance.timer_task.done():
                        self.view_instance.timer_task.cancel()
                        await interaction.response.send_message(f"❌ Đã hủy hẹn giờ trước đó. Bắt đầu hẹn giờ mới {minutes_val} phút...", ephemeral=True)
                    else:
                        await interaction.response.send_message(f"⏰ Đã đặt hẹn giờ {minutes_val} phút. Sẽ tự động chấm công sau {minutes_val} phút...", ephemeral=True)

                    # Disable buttons
                    for item in self.view_instance.children:
                        item.disabled = True
                    try:
                        await interaction.message.edit(view=self.view_instance)
                    except Exception:
                        pass
                    
                    async def delayed_checkin():
                        try:
                            await asyncio.sleep(minutes_val * 60)
                            user = await bot.fetch_user(self.view_instance.allowed_user_id)
                            await user.send(f"⏰ Đã hết {minutes_val} phút! Bắt đầu chấm công...")
                            await run_login_task()
                            
                            # After morning check-in, show afternoon automatic check-in option
                            now = datetime.now(VN_TZ)
                            target_time = now.replace(
                                hour=CHECKIN_CONFIG["AFTERNOON_NOTIFY"].hour, 
                                minute=CHECKIN_CONFIG["AFTERNOON_NOTIFY"].minute, 
                                second=0, 
                                microsecond=0
                            )
                            if target_time > now:
                                delay = (target_time - now).total_seconds()
                                
                                if self.view_instance.allowed_user_id in scheduled_tasks:
                                    scheduled_tasks[self.view_instance.allowed_user_id].cancel()

                                afternoon_msg = await user.send(
                                    f"✅ Sẵn sàng chấm công chiều lúc {target_time.strftime('%H:%M')}:",
                                    view=CancelAfternoonView(self.view_instance.allowed_user_id)
                                )

                                async def afternoon_job():
                                    try:
                                        await asyncio.sleep(delay)
                                        user = await bot.fetch_user(self.view_instance.allowed_user_id)
                                        await user.send("⏰ Đã hết giờ hãy cút khỏi công ty! Tự động chấm công...")
                                        await run_login_task()
                                        
                                        try:
                                            await afternoon_msg.delete()
                                        except Exception:
                                            pass

                                        if self.view_instance.allowed_user_id in scheduled_tasks:
                                            del scheduled_tasks[self.view_instance.allowed_user_id]
                                    except asyncio.CancelledError:
                                        pass

                                task = asyncio.create_task(afternoon_job())
                                scheduled_tasks[self.view_instance.allowed_user_id] = task
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            logger.error(f"Lỗi khi chạy hẹn giờ chấm công: {e}")

                    self.view_instance.timer_task = asyncio.create_task(delayed_checkin())

            class RunLoginView(discord.ui.View):
                def __init__(self, allowed_user_id: int, timeout: int = 60 * 120):
                    super().__init__(timeout=timeout)
                    self.allowed_user_id = allowed_user_id
                    self.timer_task = None
                    
                    # Disable auto run button if afternoon (>= 12:00)
                    now = datetime.now(VN_TZ)
                    if now.hour >= 12:
                        for child in self.children:
                            if isinstance(child, discord.ui.Button) and child.label == "Chấm công tự động":
                                child.disabled = True
                                break

                @discord.ui.button(label="Chấm công", style=discord.ButtonStyle.primary, emoji="🚀", row=0)
                async def run_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    # Only allow the specified user to click
                    if self.allowed_user_id and interaction.user.id != self.allowed_user_id:
                        await interaction.response.send_message("Bạn không có quyền thực hiện hành động này.", ephemeral=True)
                        return

                    # Acknowledge and run the task in background
                    await interaction.response.send_message("Bắt đầu chạy chấm công...", ephemeral=True)
                    # Disable buttons to prevent double-click
                    for item in self.children:
                        item.disabled = True
                    try:
                        # Edit the original message to disable the button
                        await interaction.message.edit(view=self)
                    except Exception:
                        pass

                    # Run login task in background so callback returns immediately
                    asyncio.create_task(run_login_task())

                @discord.ui.button(label="Tự động", style=discord.ButtonStyle.success, emoji="🤖", row=0)
                async def auto_run_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    # Only allow the specified user to click
                    if self.allowed_user_id and interaction.user.id != self.allowed_user_id:
                        await interaction.response.send_message("Bạn không có quyền thực hiện hành động này.", ephemeral=True)
                        return

                    # Acknowledge and run the task in background
                    await interaction.response.send_message("Bắt đầu chạy chấm công và lên lịch chiều...", ephemeral=True)
                    # Disable buttons to prevent double-click
                    for item in self.children:
                        item.disabled = True
                    try:
                        # Edit the original message to disable the button
                        await interaction.message.edit(view=self)
                    except Exception:
                        pass

                    # Run login task in background so callback returns immediately
                    asyncio.create_task(run_login_task())

                    # Check for afternoon scheduling
                    now = datetime.now(VN_TZ)
                    if now.hour < 12:
                        # Schedule for afternoon today
                        target_time = now.replace(
                            hour=CHECKIN_CONFIG["AFTERNOON_NOTIFY"].hour, 
                            minute=CHECKIN_CONFIG["AFTERNOON_NOTIFY"].minute, 
                            second=0, 
                            microsecond=0
                        )
                        if target_time > now:
                            delay = (target_time - now).total_seconds()
                            
                            # Cancel existing task if any
                            if self.allowed_user_id in scheduled_tasks:
                                scheduled_tasks[self.allowed_user_id].cancel()

                            # Send message first to get reference
                            cancel_msg = await interaction.followup.send(
                                f"✅ Đã lên lịch chấm công chiều lúc {target_time.strftime('%H:%M')}.",
                                view=CancelAfternoonView(self.allowed_user_id),
                                ephemeral=True
                            )

                            async def afternoon_job():
                                try:
                                    await asyncio.sleep(delay)
                                    user = await bot.fetch_user(self.allowed_user_id)
                                    await user.send("⏰ Đã đến giờ chiều! Tự động chấm công...")
                                    await run_login_task()
                                    
                                    # Delete the cancel message when done
                                    try:
                                        await cancel_msg.delete()
                                    except Exception:
                                        pass

                                    if self.allowed_user_id in scheduled_tasks:
                                        del scheduled_tasks[self.allowed_user_id]
                                except asyncio.CancelledError:
                                    pass

                            task = asyncio.create_task(afternoon_job())
                            scheduled_tasks[self.allowed_user_id] = task

                @discord.ui.button(label="Hẹn giờ x phút", style=discord.ButtonStyle.secondary, emoji="⏰", row=0)
                async def timer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if self.allowed_user_id and interaction.user.id != self.allowed_user_id:
                        await interaction.response.send_message("Bạn không có quyền thực hiện hành động này.", ephemeral=True)
                        return

                    await interaction.response.send_modal(TimerModal(self))

            view = RunLoginView(USER_ID)
            await user.send("Đã đến giờ chấm công. Nhấn nút bên dưới để bắt đầu:", view=view)
        except Exception as e:
            logger.error(f"Không thể gửi DM để thông báo chấm công: {e}")

@daily_task.before_loop
async def before():
    await bot.wait_until_ready()
    print("Daily task started.")

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
            daily_task.start()
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
            
            # Check if we should respond with voice (if user sent audio)
            if audio_paths:
                voice_file = f"downloads/cache/voice_reply_{message.id}.mp3"
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
