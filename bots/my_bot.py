"""
Discord Bot Main Entry Point

This is the main entry point for running the Discord bot.
All functionality has been modularized into separate files for better organization.
"""
import asyncio
from bot_core import create_bot, get_run_bot

# Create the bot with all configurations
bot = create_bot()

# Get the run function
run_bot = get_run_bot(bot)


if __name__ == "__main__":
    # Run the bot
    asyncio.run(run_bot())
