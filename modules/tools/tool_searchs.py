from datetime import datetime
from youtube_search import YoutubeSearch
# from langchain_community.document_loaders import WebBaseLoader
import requests
# import time
# import re
import random

from modules.parsers.search import parse_bing, parse_ddg, parse_tavily, _clean_url
import modules.config.config as config

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
]


def calendar_tool() -> str:
    today = datetime.now()
    return f"Thông tin thời gian hiện tại là {today.strftime('%H:%M %A %d/%m/%Y')}"


# === Backend search functions ===

def _search_bing(query: str, max_results: int = 5) -> list:
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    r = requests.get(
        "https://www.bing.com/search",
        params={"q": query, "setlang": "vi"},
        headers=headers,
        timeout=10,
    )
    if r.status_code != 200:
        return []
    return parse_bing(r.text, max_results)


def _search_ddg(query: str, max_results: int = 5) -> list:
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    data = {"q": query}
    r = requests.post(
        "https://html.duckduckgo.com/html/",
        data=data,
        headers=headers,
        timeout=10,
    )
    if r.status_code != 200:
        return []
    return parse_ddg(r.text, max_results)


def _search_tavily(query: str, max_results: int = 5) -> list:
    api_key = config.TAVILY_KEY
    if not api_key:
        return []
    r = requests.post(
        "https://api.tavily.com/search",
        json={"api_key": api_key, "query": query, "max_results": max_results},
        timeout=15,
    )
    if r.status_code != 200:
        return []
    return parse_tavily(r.json(), max_results)


# === Public interface ===

def web_search(query, max_results=5):
    backends = [_search_bing, _search_ddg, _search_tavily]
    results = []
    for backend in backends:
        try:
            results = backend(query, max_results)
            if results:
                break
        except Exception:
            continue
    text = ""
    for r in results[:max_results]:
        text += f"Title: {r['title']}\nURL: {r['url']}\nDescription: {r['description']}\n\n"
    return results, text


def search_youtube(query, limit=5):
    results = YoutubeSearch(query, max_results=limit).to_dict()
    return [{
        "title": r['title'],
        "duration": r['duration'],
        "url": f"https://youtu.be/{r['id']}",
        "views": r['views']
    } for r in results]


# def web_crawl_data(url_doc):
#     loader = WebBaseLoader(web_paths=url_doc)
#     return loader.load()


# def search_with_ddgs(query, max_results=3):
#     results, _ = web_search(query, max_results)
#     content = ""
#     for r in results:
#         docs = web_crawl_data([r["url"]])
#         time.sleep(1)
#         for doc in docs:
#             content += f"source: {doc.metadata['source']} title: {doc.metadata['title']} content: {doc.page_content}\n\n"
#     content = re.sub(r'\s+', ' ', content).strip()
#     return content