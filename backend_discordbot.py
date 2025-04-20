import discord
from discord.ext import commands
import os
import llm_chain
from dotenv import load_dotenv
import asyncio
import tools
import requests
from PIL import Image
import io
from io import BytesIO
import config
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
    image_processed = False
    temp_path = None
    # Kiểm tra và phản hồi ảnh
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                image_url = attachment.url
                print(f"🖼️ Ảnh được gửi: {image_url}")
                # Tải ảnh về
                response = requests.get(image_url)
                RGBimg = Image.open(BytesIO(response.content))

                # Lưu ảnh tạm thời (có thể dùng tên file tạm)
                temp_path = f"{config.DOWNLOAD_FOLDER}/processed_image.png"
                RGBimg.save(temp_path)
                await message.channel.send(f"📷 Ảnh cậu gửi: {image_url}")
                image_processed = True
    # Gửi hành động "đang nhập"
    if message.content or image_processed:
        async with message.channel.typing():
            loop = asyncio.get_running_loop()
            try:
                if message.content:
                    response = await loop.run_in_executor(
                        None, llm_chain.chat, message.content, temp_path
                    )
                else:
                    response = "Ảnh đã được xử lý!"
            except Exception as e:
                print("Lỗi khi gọi llm_chain.chat:", e)
                response = "⚠️ Có lỗi xảy ra khi xử lý yêu cầu."

            response = tools.format_discord_message(response)
            await message.channel.send(response)


# Khởi động server LLM và chạy bot
def main():
    # llm.start_ollama_server()
    print("🤖 Bot đang chạy trên Discord...")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
