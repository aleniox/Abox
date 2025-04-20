from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ChatAction
import os
import llm
import asyncio

from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👋 Xin chào {update.effective_user.first_name}!")


# Tự động trả lời khi có tin nhắn
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(action=ChatAction.TYPING)
    user_message = update.message.text
    response = llm.chat(user_message)
    await update.message.reply_text(response)

# Tạo ứng dụng bot
def main():
    llm.start_ollama_server()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

    print("🤖 Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
