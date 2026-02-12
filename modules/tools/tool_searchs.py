from datetime import datetime
from youtube_search import YoutubeSearch
# from duckduckgo_search import DDGS
from ddgs import DDGS
from langchain_community.document_loaders import WebBaseLoader
import re

def calendar_tool() -> str:
    today = datetime.now()
    return f"Thông tin thời gian hiện tại là {today.strftime('%H:%M %A %d/%m/%Y')}"

def web_search(query, max_results=5):
    # loader = WebBaseLoader(query, max_results=max_results)
    # return loader.load()
    
    # Tập trung tìm kiếm vào các sàn thương mại điện tử lớn để lấy giá chi tiết của sản phẩm
    ecommerce_sites = "site:shopee.vn OR site:lazada.vn OR site:tiki.vn OR site:bachhoaxanh.com OR site:cooponline.vn"
    # Thêm "giá" và loại bỏ các từ khóa chung chung bằng - để vào thẳng trang sản phẩm
    search_query = f"giá {query} {ecommerce_sites} -blog -tin-tuc -tuyen-dung"
    
    results = []
    text = ""
    try:
        # Sử dụng timelimit=None để tìm kết quả phù hợp nhất thay vì bị giới hạn bởi thời gian quá gắt gao
        for result in DDGS().text(search_query, max_results=max_results, region="vn-vi"):
            results.append({
                "title": result['title'],
                "url": result['href'],
                "description": result['body']
            })
            text += f"Title: {result['title']}\nURL: {result['href']}\nDescription: {result['body']}\n\n"
    except Exception as e:
        print(f"Lỗi tìm kiếm: {e}")
        # Fallback về tìm kiếm thông thường nếu tìm kiếm theo site bị lỗi hoặc không có kết quả
        for result in DDGS().text(query, max_results=max_results, region="vn-vi", timelimit="y"):
            results.append({
                "title": result['title'],
                "url": result['href'],
                "description": result['body']
            })
            text += f"Title: {result['title']}\nURL: {result['href']}\nDescription: {result['body']}\n\n"
            
    return results, text

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