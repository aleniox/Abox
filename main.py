import bots.discord.my_bot as my_bot
import asyncio
import logging
import time


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
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
    max_retries = 5
    retry_count = 0
    retry_delay = 5

    while retry_count < max_retries:
        try:
            main()
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"Bot crashed: {e}")
            logger.info(f"Retry {retry_count}/{max_retries} after {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

    if retry_count >= max_retries:
        logger.critical(f"Bot failed after {max_retries} retries. Exiting.")
        exit(1)
