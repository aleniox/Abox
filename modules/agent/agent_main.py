import logging
from datetime import datetime
from pathlib import Path

from modules.core import call_api_llm
import modules.config.config as config

logger = logging.getLogger(__name__)

PERSONALITY_PROMPT_FILE = Path(__file__).parent.parent / "storage" / "prompts" / "personality_prompt.md"


def _load_prompt_system() -> str:
    if PERSONALITY_PROMPT_FILE.exists():
        try:
            return PERSONALITY_PROMPT_FILE.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Lỗi đọc personality prompt: {e}")
    return "You are a helpful AI assistant."


BASE_SYSTEM = _load_prompt_system()

SCHEDULE_INSTRUCTION = """
Bạn có công cụ schedule_reminder để quản lý lịch nhắc nhở.

QUAN TRỌNG: Khi bạn thấy [TOOL_RESULT] trong lịch sử, đó là kết quả nội bộ của tool.
KHÔNG hiển thị lại [TOOL_RESULT] cho user. Chỉ dùng nó để soạn câu trả lời.

QUY TẮC XỬ LÝ LỊCH:
1. Khi user yêu cầu thêm lịch → gọi schedule_reminder(action="add") với đầy đủ thông tin
2. Sau khi nhận [TOOL_RESULT] có "PARSED" và "pending", SHOW PREVIEW và hỏi user xác nhận
3. Nếu user nói "sửa" + thông tin mới → gọi lại action="add" với thông tin đã sửa
4. Nếu user xác nhận (yes/ok/đồng ý/xác nhận) → gọi schedule_reminder(action="confirm_add", ...)
5. Nếu user nói hủy/bỏ/không → gọi schedule_reminder(action="cancel_add")
6. Khi user hỏi "xem lịch" / "danh sách" → gọi schedule_reminder(action="list")
7. Khi user muốn xóa → gọi schedule_reminder(action="delete", schedule_id="...")

PHÂN BIỆT action_type:
- action_type="reminder": CHỈ nhắc nhở text đơn giản, dùng khi user muốn nhắc làm gì đó
- action_type="web_scrape": CRAWL WEB + TỔNG HỢP BÁO CÁO.
  DÙNG action_type="web_scrape" KHI user yêu cầu:
  • "kiểm tra", "check", "xem" thông tin gì đó định kỳ (VD: "kiểm tra giá coin")
  • "tổng hợp tin", "báo cáo" từ web (VD: "tổng hợp tin tức")
  • "vào trang ... lấy thông tin"
  Khi đó cần cung cấp: url (nếu có URL cụ thể) hoặc để trống để search, và instruction mô tả cách tổng hợp
"""

SYSTEM_PROMPT = BASE_SYSTEM + "\n" + SCHEDULE_INSTRUCTION

HISTORY = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

MAX_HISTORY = 50


def process_message(message: str, user_id: int, channel=None) -> str | None:
    if not message or not message.strip():
        return None

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_msg = f"[{now}] (user_id={user_id}) {message.strip()}"

    HISTORY.append({"role": "user", "content": user_msg})

    from modules.tools.tool_schedule import schedule_tool_def, handle_schedule_tool

    tools = [schedule_tool_def]

    for attempt in range(3):
        try:
            response_data = call_api_llm.call_chat_api(
                model=config.MODEL_NAME,
                messages=HISTORY,
                tools=tools,
                stream=False
            )
            response_json = response_data.json()
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            HISTORY.pop()
            return f"❌ Lỗi: {str(e)}"

        msg = None
        if "message" in response_json:
            msg = response_json["message"]
        elif "choices" in response_json and response_json["choices"]:
            msg = response_json["choices"][0].get("message", {})

        if not msg:
            HISTORY.pop()
            return "⚠️ Không thể lấy phản hồi từ API."

        tool_calls = msg.get("tool_calls")

        if not tool_calls:
            content = msg.get("content", "")
            if content:
                HISTORY.append({"role": "assistant", "content": content})
            if len(HISTORY) > MAX_HISTORY:
                HISTORY[:] = [HISTORY[0]] + HISTORY[-(MAX_HISTORY - 1):]
            return content

        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name")
            try:
                import json
                args = json.loads(fn.get("arguments", "{}"))
            except:
                args = {}

            if name == "schedule_reminder":
                result = handle_schedule_tool(args, user_id)
            else:
                result = f"Unknown tool: {name}"

            result_str = str(result) if not isinstance(result, str) else result
            HISTORY.append({
                "role": "system",
                "content": f"[TOOL_RESULT] {name}: {result_str}"
            })

        tools = None

    HISTORY.pop()
    return "⚠️ Quá số lần thử xử lý."
