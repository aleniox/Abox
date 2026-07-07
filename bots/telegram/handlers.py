import logging
from modules.agent import agent_main

logger = logging.getLogger(__name__)


async def handle_message(update, context):
    if not update.message or not update.message.text:
        return

    msg = update.message.text.strip()
    user_id = update.effective_user.id

    logger.info(f"Telegram from {user_id}: {msg[:60]}")

    response = agent_main.process_message(msg, user_id, platform="telegram")
    if response:
        await update.message.reply_text(response)

    # Note: due schedules are checked by the periodic reminder_callback job in bot.py
