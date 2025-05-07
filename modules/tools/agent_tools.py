from datetime import datetime
from youtube_search import YoutubeSearch
import ollama
import modules.config as config
import json



def calendar_tool() -> str:
    today = datetime.now()
    return f"Thông tin thời gian hiện tại là {today.strftime('%H:%M %A %d/%m/%Y')}"

def smart_agent(user_message: str):
    """Xử lý câu hỏi, quyết định dùng tool hay LLM trả lời trực tiếp"""
    # Prompt để LLM phân tích câu hỏi
    decision_prompt = f"""/no_think
    Bạn là một trợ lý AI thông minh. Hãy phân tích câu hỏi sau và quyết định cách xử lý:
    Bạn được cung cấp các công cụ sau:
    - calender: Kiểm tra ngày tháng, thời gian, giờ, phút, giây
    - direct_answer: nếu không cần thiết sử dụng công cụ nào, hãy trả lời trực tiếp bằng tiếng Việt.
    - youtube_search: để tìm kiếm video hoặc nghe nhạc
    Trả lời ngắn gọn không được quyết định lung tung phải có căn cứ để trả lời.
    Định dạng đầu ra:
    {{"action": "direct_answer" | "calendar" | "youtube_search", "action_input": "câu query được sửa lại để sử dụng cho các công cụ"}}
    Câu hỏi: "{user_message['content']}"
    """

    # Gọi LLM để quyết định hành động
    decision = ollama.generate(model=config.MODEL_NAME_T, prompt=decision_prompt, options={"temperature": 0.7})
    # .strip().lower()
    print(f"Decision: {decision.response}")
    decision.response = decision.response.replace("<think>", "").replace("</think>", "").strip()
    if "direct_answer" in decision.response:
        # Trả lời trực tiếp bằng LLM
        return [user_message]
    elif "calendar" in decision.response:
        user_message = [{"role": "assistant", "content": calendar_tool()}, user_message]
        return user_message
    elif "youtube_search" in decision.response:
        # Tìm kiếm video trên Youtube
        query = json.loads(decision.response)
        youtube_results = search_youtube(query['action_input'])
        if not youtube_results:
            return [{"role": "assistant", "content": "Không tìm thấy video phù hợp 😢"}, user_message]
        youtube_results = "\n".join([f"""title: {r['title']} duration: {r['duration']} url: {r['url']}""" for r in youtube_results])
        user_message = [{"role": "tool", "content": f"Kết quả tìm kiếm: {youtube_results}"}, user_message]
        return user_message

def search_youtube(query, limit=5):
    results = YoutubeSearch(query, max_results=limit).to_dict()
    return [{
        "title": r['title'],
        "duration": r['duration'],
        "url": f"https://youtu.be/{r['id']}",
        "views": r['views']
    } for r in results]


# Ví dụ sử dụng
# if __name__ == "__main__":
#     user_message = {"role": "user", "content": "Tôi muốn nghe bài hát The Night"}
#     response = smart_agent(user_message)
#     print(response)