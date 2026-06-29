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

from bots.discord.bot_config import CHECKIN_CONFIG, VN_TZ, LOGIN_CSV_PATH, TASK_STYLE, VOICE_CACHE_PATH, USER_ID
import modules.tools.tool_login as tool_login
import modules.config.config as config
# import modules.tools.tool_others as tool_others
# import modules.core.voice_clone as text2speech

logger = logging.getLogger(__name__)

# Track last notification time to avoid duplicate sends
last_sent_time = None
scheduled_tasks = {}


async def execute_checkin_for_row(row, index, style, send_target):
    """Execute check-in for a single account row and send results to target"""
    host = row[0] if len(row) > 0 else "N/A"
    
    try:
        # Check if row has at least 3 columns
        if len(row) < 3:
            await send_target.send(f"⚠️ **Bỏ qua:** Dòng #{index+1} (`{host}`). Thiếu Host/User/Pass.")
            return False
        
        result = await asyncio.to_thread(
            tool_login.login_and_click,
            host=row[0], 
            username=row[1], 
            password=row[2], 
            style=style
        )
        
        # Process result
        image_path = result
        msg_content = f"✅ Host `{host}`: **Thành công.**"
        
        if isinstance(result, dict):
            image_path = result.get("screenshot")
            if result.get("message"):
                msg_content += f"\n{result['message']}"

        await send_target.send(msg_content, file=discord.File(image_path))
        return True
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e).split('\n')[0]
        if len(error_msg) > 150:
            error_msg = error_msg[:150] + "..."
        await send_target.send(f"❌ Host `{host}`: **Lỗi chung.** Chi tiết: `{type(e).__name__}: {error_msg}`")
        return False


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
        await execute_checkin_for_row(row, i, TASK_STYLE, user)
    
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
                from bots.discord.views import RunLoginView
                
                view = RunLoginView(USER_ID)
                await user.send("Đã đến giờ chấm công. Nhấn nút bên dưới để bắt đầu:", view=view)
            except Exception as e:
                logger.error(f"Không thể gửi DM để thông báo chấm công: {e}")

    @daily_task.before_loop
    async def before():
        await bot.wait_until_ready()
        print("Daily task started.")

    # Store task on bot to be started when bot is ready
    bot.daily_task = daily_task
    return daily_task


def setup_reminder_task(bot: discord.Client):
    """Setup reminder check task for user schedules"""

    @tasks.loop(minutes=1)
    async def reminder_check():
        from modules.tools.tool_schedule import get_due_schedules, delete_schedule

        now = datetime.now(VN_TZ)
        due = get_due_schedules(now.hour, now.minute)

        for sched in due:
            if not sched.get("enabled", True):
                continue
            try:
                user = await bot.fetch_user(sched["user_id"])
            except Exception as e:
                logger.error(f"Cannot fetch user {sched['user_id']}: {e}")
                continue

            action = sched.get("action", {})
            atype = action.get("type", "reminder")

            if atype == "reminder":
                await user.send(f"⏰ **Nhắc nhở:** {sched['title']}")

            elif atype == "web_scrape":
                url = action.get("url", "")
                instruction = action.get("instruction", "Tóm tắt nội dung")
                await user.send(f"🔄 Đang xử lý lịch **{sched['title']}** — crawl {url}...")

                try:
                    from modules.tools.tool_searchs import web_crawl_data
                    from modules.core.call_api_llm import call_chat_api
                    loop = asyncio.get_running_loop()
                    docs = await loop.run_in_executor(None, web_crawl_data, [url])
                    raw_text = " ".join(d.page_content for d in docs)
                    if len(raw_text) > 8000:
                        raw_text = raw_text[:8000]

                    summary_prompt = f"{instruction}\n\nNội dung:\n{raw_text}"
                    resp = call_chat_api(
                        model=config.MODEL_NAME,
                        messages=[{"role": "user", "content": summary_prompt}],
                        stream=False
                    )
                    resp_json = resp.json()
                    summary = ""
                    if "message" in resp_json:
                        summary = resp_json["message"].get("content", "")
                    elif "choices" in resp_json and resp_json["choices"]:
                        summary = resp_json["choices"][0].get("message", {}).get("content", "")

                    await user.send(f"📊 **Báo cáo {sched['title']}:**\n{summary[:2000]}")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    logger.error(f"Web_scrape error for {sched['title']}: {e}")
                    await user.send(f"❌ Lỗi khi xử lý {sched['title']}: {str(e)[:200]}")

            if sched.get("type") == "once":
                delete_schedule(sched["id"])

    @reminder_check.before_loop
    async def before():
        await bot.wait_until_ready()
        print("Reminder check task started.")

    bot.reminder_task = reminder_check
    return reminder_check
