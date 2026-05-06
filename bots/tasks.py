"""
Bot tasks for automated check-in
"""
import discord
from discord.ext import tasks
import asyncio
import csv
import logging
from datetime import datetime
import os
from pathlib import Path

from bot_config import CHECKIN_CONFIG, VN_TZ, LOGIN_CSV_PATH, TASK_STYLE, VOICE_CACHE_PATH, USER_ID
import modules.tools.tool_login as tool_login
import modules.tools.tool_others as tool_others
import modules.core.voice_clone as text2speech

logger = logging.getLogger(__name__)

# Track last notification time to avoid duplicate sends
last_sent_time = None
scheduled_tasks = {}


async def run_login_task(bot: discord.Client):
    """Execute login and check-in for all accounts"""
    global last_sent_time
    
    print("Đã đến lúc chạy login_and_click()...")
    user = await bot.fetch_user(USER_ID)
    
    try:
        with open(LOGIN_CSV_PATH, "r", encoding="utf-8") as f:
            rows = list(csv.reader(f))
    except FileNotFoundError:
        await user.send(f"❌ Không tìm thấy file {LOGIN_CSV_PATH}")
        return
    
    for i, row in enumerate(rows):
        host = row[0] if len(row) > 0 else "N/A"
        
        try:
            # Check if row has at least 3 columns
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
            
            # Process result
            image_path = result
            msg_content = f"✅ Host `{host}`: **Thành công.**"
            
            if isinstance(result, dict):
                image_path = result.get("screenshot")
                if result.get("message"):
                    msg_content += f"\n{result['message']}"

            await user.send(msg_content, file=discord.File(image_path))
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            await user.send(f"❌ Host `{host}`: **Lỗi chung.** Chi tiết: `{type(e).__name__}`")
    
    # Update last_sent_time to avoid duplicate notifications this minute
    now = datetime.now(VN_TZ)
    last_sent_time = (now.hour, now.minute)


def setup_daily_task(bot: discord.Client):
    """Setup and start the daily check-in task"""
    
    @tasks.loop(minutes=1)
    async def daily_task():
        """Task that runs every minute to check for scheduled check-in times"""
        global last_sent_time
        
        now = datetime.now(VN_TZ)
        now_time = now.time()
        current_time_tuple = (now_time.hour, now_time.minute)
        
        # Time targets for notifications
        targets = [
            CHECKIN_CONFIG["MORNING_NOTIFY"], 
            CHECKIN_CONFIG["AFTERNOON_NOTIFY"], 
            CHECKIN_CONFIG["DEBUG_NOTIFY"]
        ]
        
        # Check if current time matches any target time
        if any(now_time.hour == t.hour and now_time.minute == t.minute for t in targets):
            # Skip if already sent notification for this minute
            if last_sent_time == current_time_tuple:
                return
            
            # Update sent time
            last_sent_time = current_time_tuple
            
            try:
                # Send DM with check-in options
                user = await bot.fetch_user(USER_ID)
                from views import RunLoginView
                
                view = RunLoginView(USER_ID)
                await user.send("Đã đến giờ chấm công. Nhấn nút bên dưới để bắt đầu:", view=view)
            except Exception as e:
                logger.error(f"Không thể gửi DM để thông báo chấm công: {e}")

    @daily_task.before_loop
    async def before():
        await bot.wait_until_ready()
        print("Daily task started.")

    daily_task.start()
    return daily_task
