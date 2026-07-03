import asyncio
from crawl4ai import AsyncWebCrawler
import threading

async def _crawl_async(url: str):
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return result.markdown
    except Exception as e:
        return f"Lỗi khi crawl dữ liệu: {e}"

def crawl_web(url: str):
    result = None
    exception = None

    def _worker():
        nonlocal result, exception
        try:
            # Chạy loop cục bộ trên thread này
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_crawl_async(url))
            loop.close()
        except Exception as e:
            exception = e

    try:
        asyncio.get_running_loop()
        in_loop = True
    except RuntimeError:
        in_loop = False

    if in_loop:
        # Nếu đang ở trong một event loop (ví dụ bot discord), chạy trên thread khác để không bị lỗi RuntimeError
        thread = threading.Thread(target=_worker)
        thread.start()
        thread.join()
        if exception:
            return f"Lỗi chạy thread crawl: {exception}"
        return result
    else:
        # Nếu không ở trong loop nào thì chạy bình thường
        return asyncio.run(_crawl_async(url))
