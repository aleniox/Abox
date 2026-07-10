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


async def run_web():
    import uvicorn
    import os
    from servers.web_ui import app
    
    ssl_key = "storage/certs/key.pem"
    ssl_cert = "storage/certs/cert.pem"
    
    if os.path.exists(ssl_key) and os.path.exists(ssl_cert):
        logger.info(f"Starting Web UI with HTTPS on port 5000 (certs loaded from {ssl_cert})")
        config = uvicorn.Config(
            app, 
            host="0.0.0.0", 
            port=5000, 
            log_level="info",
            ssl_keyfile=ssl_key,
            ssl_certfile=ssl_cert
        )
    else:
        logger.info("Starting Web UI on http://localhost:5050 (inside Docker: port 5000) - HTTP Mode")
        config = uvicorn.Config(app, host="0.0.0.0", port=5000, log_level="info")
        
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    logger.info("Starting all services...")
    await asyncio.gather(run_discord(), run_web())


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
