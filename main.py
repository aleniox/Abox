import asyncio
import logging
import time
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_discord():
    from bots.discord.my_bot import run_bot
    logger.info("Starting Discord bot...")
    await run_bot()


async def run_telegram():
    from bots.telegram.bot import run_telegram as tg_run
    logger.info("Starting Telegram bot...")
    await tg_run()


async def main():
    logger.info("Starting both bots...")

    tasks = [
        asyncio.create_task(run_discord()),
        asyncio.create_task(run_telegram()),
    ]

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    for task in done:
        exc = task.exception()
        if exc:
            logger.error(f"Bot failed: {exc}")
    for task in pending:
        task.cancel()


if __name__ == "__main__":
    max_retries = 5
    retry_count = 0
    retry_delay = 5

    while retry_count < max_retries:
        try:
            asyncio.run(main())
            break
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"Main crashed: {e}")
            logger.info(f"Retry {retry_count}/{max_retries} after {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

    if retry_count >= max_retries:
        logger.critical("Failed after max retries.")
        sys.exit(1)
