"""
Discord bot commands
"""
import discord
from discord.ext import commands
from discord import Embed, Color
import csv
import logging
import os
from pathlib import Path

from bots.discord.views import FormView, RunLoginView, ShutdownConfirm
from bots.discord import bot_config

logger = logging.getLogger(__name__)


def setup_commands(bot: commands.Bot):
    """Register all commands with the bot"""
    
    @bot.hybrid_command(name="form")
    async def form(ctx):
        """Hiện form điền thông tin chấm công"""
        await ctx.send("📋 Bấm vào nút bên dưới để điền form:", view=FormView())

    @bot.hybrid_command(name="ckin")
    async def checkin_and_out(ctx, style: str = 'ls'):
        """Chạy chấm công thủ công"""
        async with ctx.channel.typing():
            rows = []
            from bots.discord.bot_config import LOGIN_CSV_PATH
            from bots.discord.tasks import execute_checkin_for_row
            
            try:
                with open(LOGIN_CSV_PATH, "r", encoding="utf-8") as f:
                    rows = list(csv.reader(f))
            except FileNotFoundError:
                await ctx.channel.send(f"❌ **Lỗi:** Không tìm thấy tệp `{LOGIN_CSV_PATH}`.")
                return

            print(f"Bắt đầu chấm công, style: {style}")
            
            for i, row in enumerate(rows):
                await execute_checkin_for_row(row, i, style, ctx.channel)

        await ctx.channel.send("Đã hoàn tất quá trình chấm công.")

    @bot.hybrid_command(name="start")
    async def start_bot(ctx):
        """Lưu User ID của bạn để nhận thông báo"""
        user_id = ctx.author.id
        env_path = Path(".env")

        lines = env_path.read_text(encoding="utf-8").splitlines()
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("USER_ID"):
                new_lines.append(f"USER_ID={user_id}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"USER_ID={user_id}")
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        from dotenv import load_dotenv
        load_dotenv(override=True)
        from bots.discord import bot_config
        bot_config.USER_ID = user_id

        await ctx.send(f"✅ Đã lưu User ID `{user_id}`. Bot sẽ gửi thông báo chấm công đến bạn.")

    @bot.hybrid_command(name="info")
    async def send_info(ctx):
        """Xem thông tin bot"""
        embed = Embed(
            title=f"🎉 Chào mừng đến với {bot.user.name} Bot",
            description=f"Tôi là trợ lý ảo của {ctx.author.display_name} trên Discord!",
            color=Color.fuchsia()
        )
        
        embed.set_thumbnail(url="https://image.cdn2.seaart.me/2025-05-03/d0b1a4de878c73a4afrg/41459208059d8a6591789e1751030de8_high.webp")
        embed.add_field(name="🤖 Tính năng", value="• Trò chuyện thông minh\n• Tìm kiếm thông tin\n• Giải trí", inline=False)
        embed.set_footer(text=f"{bot.user.name} Bot © 2025")
        
        await ctx.send(embed=embed)

    @bot.hybrid_command(name="shutdown")
    async def shutdown_bot(ctx):
        """Tắt máy tính từ xa"""
        if ctx.author.id != bot_config.USER_ID:
            await ctx.send("❌ Bạn không có quyền thực hiện lệnh này.")
            return

        view = ShutdownConfirm(ctx)
        await ctx.send("⚠️ **Cảnh báo:** Bạn có chắc muốn tắt máy tính?", view=view)
