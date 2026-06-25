"""
Discord bot commands
"""
import discord
from discord.ext import commands
from discord import Embed, Color
import csv
import asyncio
import logging
from pathlib import Path

from bots.discord.views import FormView, RunLoginView
import modules.tools.tool_login as tool_login

logger = logging.getLogger(__name__)


def setup_commands(bot: commands.Bot):
    """Register all commands with the bot"""
    
    @bot.command()
    async def form(ctx):
        """Command to show form for entering login info"""
        await ctx.send("📋 Bấm vào nút bên dưới để điền form:", view=FormView())

    @bot.command(name="ckin")
    async def checkin_and_out(ctx, style: str = 'ls'):
        """Command to manually trigger check-in"""
        async with ctx.channel.typing():
            rows = []
            from bots.discord.bot_config import LOGIN_CSV_PATH
            from bots.discord.tasks import execute_checkin_for_row
            
            # 1. Read CSV file
            try:
                with open(LOGIN_CSV_PATH, "r", encoding="utf-8") as f:
                    rows = list(csv.reader(f))
            except FileNotFoundError:
                await ctx.channel.send(f"❌ **Lỗi:** Không tìm thấy tệp `{LOGIN_CSV_PATH}`.")
                return

            print(f"Bắt đầu chấm công, style: {style}")
            
            # 2. Process each account
            for i, row in enumerate(rows):
                await execute_checkin_for_row(row, i, style, ctx.channel)

        # 3. Complete
        await ctx.channel.send("Đã hoàn tất quá trình chấm công.")

    @bot.command(name="info")
    async def send_info(ctx):
        """Send bot info message"""
        embed = Embed(
            title=f"🎉 Chào mừng đến với {bot.user.name} Bot",
            description=f"Tôi là trợ lý ảo của {ctx.author.display_name} trên Discord!",
            color=Color.fuchsia()
        )
        
        embed.set_thumbnail(url="https://image.cdn2.seaart.me/2025-05-03/d0b1a4de878c73a4afrg/41459208059d8a6591789e1751030de8_high.webp")
        embed.add_field(name="🤖 Tính năng", value="• Trò chuyện thông minh\n• Tìm kiếm thông tin\n• Giải trí", inline=False)
        embed.set_footer(text=f"{bot.user.name} Bot © 2025")
        
        await ctx.send(embed=embed)
