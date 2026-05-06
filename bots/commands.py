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

from views import FormView, RunLoginView
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
            
            # 1. Read CSV file
            try:
                with open("downloads/cache/login_info.csv", "r", encoding="utf-8") as f:
                    rows = list(csv.reader(f))
            except FileNotFoundError:
                await ctx.channel.send("❌ **Lỗi:** Không tìm thấy tệp `login_info.csv`.")
                return

            print(f"Bắt đầu chấm công, style: {style}")
            
            # 2. Process each account
            for i, row in enumerate(rows):
                host = row[0] if len(row) > 0 else "N/A"
                
                try:
                    # Check if row has at least 3 columns
                    if len(row) < 3:
                        await ctx.channel.send(f"⚠️ **Bỏ qua:** Dòng #{i+1} (`{host}`). Thiếu Host/User/Pass.")
                        continue
                        
                    result = await asyncio.to_thread(
                        tool_login.login_and_click,
                        host=row[0], 
                        username=row[1], 
                        password=row[2], 
                        style=style
                    )
                    
                    # Process result (can be image path or dict with message)
                    image_path = result
                    msg_content = f"✅ Host `{host}`: **Thành công.**"
                    
                    if isinstance(result, dict):
                        image_path = result.get("screenshot")
                        if result.get("message"):
                            msg_content += f"\n{result['message']}"
                    
                    await ctx.channel.send(msg_content, file=discord.File(image_path))

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    await ctx.channel.send(f"❌ Host `{host}`: **Lỗi chung.** Chi tiết: `{type(e).__name__}`")

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
