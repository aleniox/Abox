import bots.my_bot as my_bot
import asyncio
import logging
# import modules.core.agent_chat as agent_chat


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Start the bot with reconnection handling."""
    # agent_chat.start_ollama_server()
    logger.info("Starting Discord bot with reconnection handling...")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(my_bot.run_bot())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        loop.run_until_complete(my_bot.bot.close())
        loop.close()
        logger.info("Bot has shut down.")

if __name__ == "__main__":
    main()
    
# chatbot.aipt.vn