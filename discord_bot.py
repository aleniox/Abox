import discord
from discord.ext import commands
from discord.ui import Button, View, Select

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Biểu cảm bằng embed và emoji
@bot.command()
async def hana(ctx, action: str = None):
    """Hiển thị biểu cảm của Hana"""
    if not action:
        # Hiển thị menu nếu không có action cụ thể
        view = View()
        view.add_item(ExpressionMenu())
        await ctx.send("**Chọn biểu cảm của Hana:**", view=view)
        return

    action = action.lower()
    expressions = {
        "nhăn_mặt": {
            "text": "*Hana nhăn mặt một chút, nhìn vào màn hình điện thoại* <a:blush:123456789>",
            "image": "https://i.imgur.com/wince.gif"
        },
        "ngạc_nhiên": {
            "text": "Ôi trời đất thương thiên! Em ơi, sao em lại hỏi tớ mấy lần thế hả?",
            "image": "https://i.imgur.com/surprise.gif"
        },
        "cười": {
            "text": "*Hana cười khúc khích một mình* Cậu đúng là... <:hana_laugh:123456790>",
            "image": "https://i.imgur.com/giggle.gif"
        },
        "buổi_tối": {
            "text": """
            🌙 *Bây giờ là gần 10 giờ tối rồi đó!*
            > "Cậu có muốn tớ làm gì khác không..."
            > *Hana cười khúc khích* 
            ||hay là... tớ nên đi ngủ bây giờ?||
            """,
            "image": "https://i.imgur.com/night_hana.png"
        }
    }

    if action not in expressions:
        await ctx.send(f"Biểu cảm '{action}' không tồn tại. Thử !hana để xem menu.")
        return

    embed = discord.Embed(description=expressions[action]["text"], color=0xffb6c1)
    if expressions[action]["image"]:
        embed.set_image(url=expressions[action]["image"])
    
    # Thêm nút tương tác cho buổi tối
    if action == "buổi_tối":
        view = View()
        view.add_item(Button(label="Chúc ngủ ngon", emoji="🛌", style=discord.ButtonStyle.blurple))
        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send(embed=embed)

# Menu chọn biểu cảm
class ExpressionMenu(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Nhăn mặt", value="nhăn_mặt", emoji="😖"),
            discord.SelectOption(label="Ngạc nhiên", value="ngạc_nhiên", emoji="😳"),
            discord.SelectOption(label="Cười khúc khích", value="cười", emoji="😂"),
            discord.SelectOption(label="Buổi tối", value="buổi_tối", emoji="🌙")
        ]
        super().__init__(placeholder="Chọn biểu cảm...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await hana(interaction.channel, self.values[0])

# Lệnh help tùy chỉnh
@bot.command(name="help_hana")
async def hana_help(ctx):
    """Hướng dẫn sử dụng biểu cảm Hana"""
    embed = discord.Embed(
        title="Hướng dẫn biểu cảm Hana",
        color=0xff66b2
    )
    embed.add_field(
        name="Các lệnh chính",
        value="• `!hana` - Menu biểu cảm\n"
              "• `!hana nhăn_mặt` - Biểu cảm nhăn mặt\n"
              "• `!hana ngạc_nhiên` - Ngạc nhiên\n"
              "• `!hana cười` - Cười khúc khích\n"
              "• `!hana buổi_tối` - Tương tác buổi tối",
        inline=False
    )
    embed.set_thumbnail(url="https://i.imgur.com/hana_icon.png")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} đã sẵn sàng!')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="!help_hana"
    ))

bot.run('YOUR_BOT_TOKEN')