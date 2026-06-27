"""
Bot core initialization
"""
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv

from bots.discord.bot_config import TOKEN, USER_ID, MAX_RETRIES, RETRY_DELAY
from bots.discord.commands import setup_commands
from bots.discord.events import setup_events, get_run_bot_func
from bots.discord.tasks import setup_daily_task, setup_reminder_task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def create_bot() -> commands.Bot:
    """Create and configure Discord bot"""
    # Initialize bot with intents
    intents = discord.Intents.default()
    intents.message_content = True
    
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    # Add scheduled_tasks attribute for managing check-in tasks
    bot.scheduled_tasks = {}
    
    # Setup all components
    setup_commands(bot)
    setup_events(bot, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY)
    setup_daily_task(bot)
    setup_reminder_task(bot)
    
    return bot


def get_run_bot(bot: commands.Bot):
    """Get the run_bot function for starting the bot"""
    return get_run_bot_func(bot, TOKEN, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY)
