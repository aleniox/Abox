from datetime import datetime
from youtube_search import YoutubeSearch
from duckduckgo_search import DDGS
from langchain_community.document_loaders import WebBaseLoader
import re

def calendar_tool() -> str:
    today = datetime.now()
    return f"Thông tin thời gian hiện tại là {today.strftime('%H:%M %A %d/%m/%Y')}"


def search_youtube(query, limit=5):
    results = YoutubeSearch(query, max_results=limit).to_dict()
    return [{
        "title": r['title'],
        "duration": r['duration'],
        "url": f"https://youtu.be/{r['id']}",
        "views": r['views']
    } for r in results]

def web_crawl_data(url_doc):
    loader = WebBaseLoader(
            web_paths=url_doc)
    # print(loader)
    document_to_compare = loader.load()
    return document_to_compare

def search_with_ddgs(query, max_results=3):
    import time
    tool = DDGS()
    content=""
    search_results = tool.text(query, region="vn-vi", max_results=max_results)
    print(search_results)
    for list_web in search_results:
        docs = web_crawl_data([list_web["href"]])
        time.sleep(1)
        for doc in docs:
            content += f"source: {doc.metadata['source']} title: {doc.metadata['title']} content: {doc.page_content}\n\n"
    content = re.sub(r'\s+', ' ', content)  # Thay thế tất cả khoảng trắng (bao gồm \n, \t) bằng một dấu cách đơn
    content = content.strip()
    return content