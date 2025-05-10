from datetime import datetime
from youtube_search import YoutubeSearch

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