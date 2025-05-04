import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOK')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Character Configuration
class HanaCharacter:
    # Basic Info
    NAME = "Hana"
    NICKNAME = "Hana-chan"
    AGE = "18"
    GENDER = "Nữ"
    THEME_COLOR = 0xFFB6C1  # Pastel Pink
    AVATAR_URL = "https://i.imgur.com/Jr6Qf6n.gif"
    
    # Expressions
    EXPRESSIONS = {
        "happy": {
            "text": "*Hana cười khúc khích*",
            "emoji": "😊",
            "image": "https://image.cdn2.seaart.me/2025-05-04/d0bfnode878c739d7ks0/842ceab6c2991f0469f9698abd886e07_high.webp"
        },
        "surprised": {
            "text": "*Hana giật mình, mắt mở to*",
            "emoji": "😳",
            "image": "https://image.cdn2.seaart.me/2025-05-04/d0bfpste878c738ai7kg/3787d2a0b397a8752ebece478044be44_high.webp"
        },
        "embarrassed": {
            "text": "*Hana đỏ mặt, nhìn xuống đất*",
            "emoji": "😖",
            "image": "https://image.cdn2.seaart.me/2025-05-04/d0bfq8de878c739dp8vg/755c829266fe9b6fd6f3f03f5f974e49_high.webp"
        },
        "sad": {
            "text": "*Hana cúi đầu, giọng nhỏ dần*",
            "emoji": "😢",
            "image": "https://image.cdn2.seaart.me/2025-05-04/d0bfs7le878c73ddt3ug/7b7031d8eb9fce5dcc329059fc9603eb_high.webp"
        },
    }

# Display System
class HanaDisplay:
    @staticmethod
    async def show_expression(ctx, mood: str):
        """Show Hana's expression"""
        expr = HanaCharacter.EXPRESSIONS.get(mood, HanaCharacter.EXPRESSIONS["happy"])
        
        embed = discord.Embed(
            description=f"{expr['emoji']} {expr['text']}",
            color=HanaCharacter.THEME_COLOR
        )
        embed.set_image(url=expr["image"])
        embed.set_footer(
            text=f"{HanaCharacter.NAME} • {HanaCharacter.NICKNAME}",
            icon_url=HanaCharacter.AVATAR_URL
        )
        
        await ctx.send(embed=embed)

    @staticmethod
    async def show_random_expression(ctx):
        """Show random Hana expression"""
        mood = random.choice(list(HanaCharacter.EXPRESSIONS.keys()))
        await HanaDisplay.show_expression(ctx, mood)

# Commands
@bot.command(name="hana")
async def hana_command(ctx):
    """Random Hana expression"""
    await HanaDisplay.show_random_expression(ctx)

@bot.command(name="express")
async def express_command(ctx, mood: str = None):
    """Show specific expression
    Usage: !express [happy/surprised/embarrassed/sad]
    """
    if mood and mood in HanaCharacter.EXPRESSIONS:
        await HanaDisplay.show_expression(ctx, mood)
    else:
        await ctx.send(f"Vui lòng chọn một trong các biểu cảm: {', '.join(HanaCharacter.EXPRESSIONS.keys())}")

@bot.command(name="info")
async def info_command(ctx):
    """Show Hana's info"""
    embed = discord.Embed(
        title=f"🌸 Thông tin về {HanaCharacter.NAME}",
        color=HanaCharacter.THEME_COLOR
    )
    
    embed.add_field(name="Tên", value=HanaCharacter.NAME, inline=True)
    embed.add_field(name="Biệt danh", value=HanaCharacter.NICKNAME, inline=True)
    embed.add_field(name="Tuổi", value=HanaCharacter.AGE, inline=True)
    
    embed.set_thumbnail(url=HanaCharacter.AVATAR_URL)
    embed.set_image(url="https://i.imgur.com/banner_hana.png")
    
    # Create interaction buttons
    view = View()
    for mood, expr in HanaCharacter.EXPRESSIONS.items():
        button = Button(
            label=expr["text"][1:-1],  # Remove asterisks
            emoji=expr["emoji"],
            style=discord.ButtonStyle.secondary,
            custom_id=f"expr_{mood}"
        )
        view.add_item(button)
    
    await ctx.send(embed=embed, view=view)

# Button Interactions
@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id.startswith("expr_"):
            mood = custom_id[5:]
            if mood in HanaCharacter.EXPRESSIONS:
                await HanaDisplay.show_expression(interaction, mood)
                await interaction.response.defer()

# Run Bot
@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} đã sẵn sàng!')
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{HanaCharacter.NICKNAME} | !help"
        )
    )

if __name__ == "__main__":
    bot.run(TOKEN)