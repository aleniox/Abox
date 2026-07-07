import logging
import os
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application, MessageHandler, filters

from bots.telegram.handlers import handle_message
from modules.tools.tool_schedule import get_due_reports

load_dotenv()
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is required in .env")


async def reminder_callback(context):
    """Check and execute due Telegram schedules"""
    try:
        reports = get_due_reports(platform="telegram")
        for user_id, text in reports:
            try:
                await context.bot.send_message(chat_id=user_id, text=text)
            except Exception as e:
                logger.error(f"Telegram send to {user_id} failed: {e}")
    except Exception as e:
        logger.error(f"Reminder callback error: {e}")


async def run_telegram():
    """Start the Telegram bot"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Reminder job every 60 seconds
    jq = app.job_queue
    if jq:
        jq.run_repeating(reminder_callback, interval=60, first=10)

    logger.info("Telegram bot started")
    await app.run_polling(allowed_updates=["messages"])
