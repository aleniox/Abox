# # Importing libraries and modules
# import os
# import discord
# from discord.ext import commands
# from discord import app_commands
# from dotenv import load_dotenv


# # Environment variables for tokens and other sensitive data
# load_dotenv()
# TOKEN = os.getenv("DISCORD_TOK")
# # Setup of intents. Intents are permissions the bot has on the server
# intents = discord.Intents.default()
# intents.message_content = True

# # Bot setup
# bot = commands.Bot(command_prefix="!", intents=intents)

# # Bot ready-up code
# @bot.event
# async def on_ready():
#     await bot.tree.sync()
#     print(f"{bot.user} is online!")

# bot.run(TOKEN)


import discord
from discord.ext import commands
import os
import llm
from dotenv import load_dotenv
import asyncio
import tools
# Load biến môi trường
load_dotenv()
TOKEN = os.getenv("DISCORD_TOK")

# Khởi tạo bot với prefix là "!"
intents = discord.Intents.default()
intents.message_content = True  # Bật quyền truy cập nội dung tin nhắn

bot = commands.Bot(command_prefix="!", intents=intents)

# Sự kiện khi bot sẵn sàng
@bot.event
async def on_ready():
    print(f"🤖 Bot đã đăng nhập với tên: {bot.user}")

# Lệnh !start
@bot.command()
async def start(ctx):
    await ctx.send(f"👋 Xin chào {ctx.author.display_name}!")

# Xử lý tin nhắn tự động (không phải lệnh)
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # Kiểm tra và phản hồi ảnh
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                image_url = attachment.url
                print(f"🖼️ Ảnh được gửi: {image_url}")
                await message.channel.send(f"📷 Ảnh bạn gửi: {image_url}")

    # Gửi hành động "đang nhập"
    async with message.channel.typing():
        response = llm.chat(message.content)
        response = tools.format_discord_message(response)
        print("🤖 Bot trả lời:", response)
        await message.channel.send(response)


# Khởi động server LLM và chạy bot
def main():
    # llm.start_ollama_server()
    print("🤖 Bot đang chạy trên Discord...")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
