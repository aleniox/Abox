"""
Bot tasks for automated check-in
"""
import discord
from discord.ext import tasks
import asyncio
import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path

from bots.discord.bot_config import CHECKIN_CONFIG, VN_TZ, LOGIN_CSV_PATH, TASK_STYLE, VOICE_CACHE_PATH, USER_ID
from bots.discord.views import ReminderView
import modules.tools.tool_login as tool_login
import modules.config.config as config

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
    bot.pending_reminders = {}

    async def _send_reminder_embed(user: discord.User, sched: dict):
        embed = discord.Embed(
            title="⏰ Nhắc nhở",
            description=sched["title"],
            color=discord.Color.purple(),
            timestamp=datetime.now(VN_TZ)
        )
        embed.set_footer(text="Rei - Người bạn ấm áp")
        view = ReminderView(user.id, sched["id"])
        await user.send(f"<@{user.id}>", embed=embed, view=view)

    async def _followup_reminder(pr: dict):
        try:
            user = await bot.fetch_user(pr["user_id"])
            sched_id = None
            for sid, p in bot.pending_reminders.items():
                if p is pr:
                    sched_id = sid
                    break
            if not sched_id:
                return
            embed = discord.Embed(
                title="⏰ Nhắc lại",
                description=pr["title"],
                color=discord.Color.purple(),
                timestamp=datetime.now(VN_TZ)
            )
            embed.set_footer(text="Rei - Người bạn ấm áp (lần %d/3)" % (pr["sent_count"] + 1))
            view = ReminderView(user.id, sched_id)
            await user.send(f"<@{user.id}>", embed=embed, view=view)
            pr["sent_count"] += 1
            pr["last_sent"] = datetime.now()
            pr["snoozed_until"] = None
        except Exception as e:
            logger.error(f"Follow-up reminder error: {e}")

    @tasks.loop(minutes=1)
    async def reminder_check():
        from modules.tools.tool_schedule import get_due_schedules, delete_schedule

        now = datetime.now(VN_TZ)
        due = get_due_schedules(now.hour, now.minute, platform="discord")

        # Follow-up check for pending reminders
        to_remove = []
        for sched_id, pr in list(bot.pending_reminders.items()):
            if pr["dismissed"]:
                to_remove.append(sched_id)
                continue
            if pr["sent_count"] >= 3:
                to_remove.append(sched_id)
                continue
            if pr["snoozed_until"] and datetime.now().timestamp() < pr["snoozed_until"]:
                continue
            if (datetime.now() - pr["last_sent"]).total_seconds() >= 300:
                await _followup_reminder(pr)
        for sid in to_remove:
            bot.pending_reminders.pop(sid, None)

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
                # Track and send with embed + buttons + ping
                sched_id = sched["id"]
                if sched_id not in bot.pending_reminders:
                    bot.pending_reminders[sched_id] = {
                        "user_id": sched["user_id"],
                        "title": sched["title"],
                        "sent_count": 1,
                        "dismissed": False,
                        "snoozed_until": None,
                        "last_sent": datetime.now()
                    }
                else:
                    bot.pending_reminders[sched_id]["sent_count"] += 1
                    bot.pending_reminders[sched_id]["last_sent"] = datetime.now()
                await _send_reminder_embed(user, sched)

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
                    summary = ""
                    if "message" in resp:
                        summary = resp["message"].get("content", "")
                    elif "choices" in resp and resp["choices"]:
                        summary = resp["choices"][0].get("message", {}).get("content", "")

                    await user.send(f"📊 **Báo cáo {sched['title']}:**\n{summary[:2000]}")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    logger.error(f"Web_scrape error for {sched['title']}: {e}")
                    await user.send(f"❌ Lỗi khi xử lý {sched['title']}: {str(e)[:200]}")

            elif atype == "agent_task":
                prompt = action.get("prompt", sched["title"])
                await user.send(f"🤖 Đang xử lý tác vụ: **{sched['title']}**...")
                try:
                    from modules.agent.agent_main import process_message
                    result = process_message(prompt, sched["user_id"], channel=None,
                        task_context="<task_context>Đây là tác vụ tự động theo lịch trình đã định sẵn. BẮT BUỘC dùng công cụ (search_web, url_search) để lấy dữ liệu mới nhất. Sau khi search_web, dùng url_search để đọc nội dung từ các URL có kết quả. Có thể gọi nhiều lần nếu cần. Chỉ output answer khi đã có thông tin cụ thể. KHÔNG hỏi lại người dùng.</task_context>")
                    text = result["text"] if isinstance(result, dict) else result
                    await user.send(f"📊 **Báo cáo {sched['title']}:**\n{text[:2000]}")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    logger.error(f"Agent_task error for {sched['title']}: {e}")
                    await user.send(f"❌ Lỗi khi xử lý {sched['title']}: {str(e)[:200]}")

            if sched.get("type") == "once":
                delete_schedule(sched["id"])

    @reminder_check.before_loop
    async def before():
        await bot.wait_until_ready()
        print("Reminder check task started.")

    bot.reminder_task = reminder_check
    return reminder_check
