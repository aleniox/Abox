import json
import logging
import base64
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def clean_excessive_newlines(text):
    return re.sub(r'\n{3,}', '\n\n', text.strip())

from modules.core import call_api_llm
import modules.config.config as config
import modules.memory.memory as memory

# Tool imports
from modules.tools.tool_schedule import schedule_tool_def, handle_schedule_tool
from modules.tools.tools_call import (
    calculus_tool, search_web_tool, url_search_tool,
    generate_image_tools, generate_voice_tools, calculus_calculator
)
from modules.tools.tool_searchs import web_search, web_crawl_data
from modules.tools.tool_generate import call_api_generate_image
from modules.tools.tool_expense import expense_tool_def, handle_expense_tool

logger = logging.getLogger(__name__)

# --- Personalization ---
PROFILE_DIR = Path("storage/profiles")
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

# --- System prompt ---
PERSONALITY_PROMPT_FILE = Path(__file__).parent.parent.parent / "storage" / "prompts" / "personality_prompt.md"


def _load_prompt_system() -> str:
    if PERSONALITY_PROMPT_FILE.exists():
        try:
            return PERSONALITY_PROMPT_FILE.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Lỗi đọc personality prompt: {e}")
    return "You are a helpful AI assistant."


BASE_SYSTEM = _load_prompt_system()


def _load_user_profile(user_id: int) -> dict:
    profile_path = PROFILE_DIR / f"user_{user_id}.json"
    if profile_path.exists():
        try:
            return json.loads(profile_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"name": None, "preferences": {}, "created_at": datetime.now().isoformat()}


def _build_system_prompt(user_id: int) -> str:
    profile = _load_user_profile(user_id)
    prompt = BASE_SYSTEM

    if profile.get("name"):
        prompt += f"\n\nNgười dùng của bạn tên là {profile['name']}."
    prefs = profile.get("preferences", {})
    if prefs.get("habits"):
        prompt += f"\nThói quen của user: {', '.join(prefs['habits'])}."
    if prefs.get("interests"):
        prompt += f"\nSở thích: {', '.join(prefs['interests'])}."

    prompt += """

Bạn có các công cụ sau. Hãy dùng công cụ phù hợp khi user yêu cầu:

1. **schedule_reminder** - Quản lý lịch nhắc nhở (thêm, xem, xóa, hẹn giờ)
2. **calculus_calculator** - Tính toán đạo hàm, tích phân, biểu thức số học
3. **search_web** - Tìm kiếm thông tin trên internet
4. **url_search** - Đọc nội dung từ URL cụ thể
5. **generate_image** - Tạo ảnh từ mô tả văn bản
6. **generate_voice** - Tạo giọng nói từ văn bản
7. **expense_tracker** - Ghi chép và xem chi tiêu cá nhân

QUAN TRỌNG: Khi bạn thấy [TOOL_RESULT] trong lịch sử, đó là kết quả nội bộ của tool.
KHÔNG hiển thị lại [TOOL_RESULT] cho user. Chỉ dùng nó để soạn câu trả lời.

QUY TẮC XỬ LÝ LỊCH (schedule_reminder):
1. User yêu cầu thêm lịch → gọi schedule_reminder(action="add") với đầy đủ thông tin
2. Sau khi nhận [TOOL_RESULT] có "PARSED" và "pending", SHOW PREVIEW và hỏi user xác nhận
3. Nếu user nói "sửa" + thông tin mới → gọi lại action="add" với thông tin đã sửa
4. Nếu user xác nhận → gọi schedule_reminder(action="confirm_add", ...)
5. Nếu user hủy → gọi schedule_reminder(action="cancel_add")
6. User hỏi "xem lịch" → gọi schedule_reminder(action="list")
7. User muốn xóa → gọi schedule_reminder(action="delete", schedule_id="...")"""
    return prompt


# --- Tool registry ---
ALL_TOOLS = [
    schedule_tool_def,
    calculus_tool,
    search_web_tool,
    url_search_tool,
    generate_image_tools,
    generate_voice_tools,
    expense_tool_def,
]


# --- History ---
HISTORY: List[Dict] = []


def _load_history(user_id: int):
    global HISTORY
    raw = memory.load_chat_history()
    system_prompt = _build_system_prompt(user_id)
    HISTORY = [{"role": "system", "content": system_prompt}] + raw[1:] if raw else [{"role": "system", "content": system_prompt}]


def _save_history():
    memory.save_chat_history(HISTORY[1:])


# --- Image encoding ---
def _encode_image(image_path: Path) -> Optional[str]:
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Lỗi encode ảnh {image_path}: {e}")
        return None


# --- Tool routing ---
def _execute_tool(name: str, args: dict) -> Tuple[str, Optional[str]]:
    """
    Execute a tool by name with given args.
    Returns (result_text, optional_generated_image_path)
    """
    generated_image = None

    try:
        if name == "calculus_calculator":
            result = calculus_calculator(
                expression=args.get("expression"),
                operation=args.get("operation"),
                evaluate=args.get("evaluate"),
                variable=args.get("variable"),
                lower_bound=args.get("lower_bound"),
                upper_bound=args.get("upper_bound")
            )
        elif name == "search_web":
            contexts = web_search(query=args["query"])
            result = contexts[1]
        elif name == "url_search":
            docs = web_crawl_data(url_doc=args["url"])
            result = '\n'.join(
                f"Source: {doc.metadata.get('source')}, Title: {doc.metadata.get('title')}, "
                f"Language: {doc.metadata.get('language', 'None')}, "
                f"Page_content: {clean_excessive_newlines(doc.page_content)}"
                for doc in docs
            )
        elif name == "generate_image":
            img_path = call_api_generate_image(args)
            generated_image = img_path
            result = f"Đã tạo ảnh và lưu tại {img_path}"
        elif name == "generate_voice":
            result = f"Đã tạo giọng nói cho: {args.get('text', '')}"
        elif name == "expense_tracker":
            result = handle_expense_tool(args=args)
        elif name == "schedule_reminder":
            result = handle_schedule_tool(args, args.get("_user_id", 0))
        else:
            result = f"Tool không hỗ trợ: {name}"
    except Exception as e:
        import traceback
        traceback.print_exc()
        result = f"Lỗi khi chạy tool {name}: {str(e)}"

    return result, generated_image


# --- Main entry point ---
def process_message(message: str, user_id: int, channel=None,
                     image_paths: Optional[List[Path]] = None,
                     audio_paths: Optional[List[Path]] = None):
    if not message and not image_paths:
        return None

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _load_history(user_id)

    # Build user content (text + images as base64)
    user_msg = f"[{now}] (user_id={user_id}) {message.strip()}"
    if image_paths:
        content_parts = [{"type": "text", "text": user_msg}]
        for img_path in image_paths:
            b64 = _encode_image(img_path)
            if b64:
                ext = Path(img_path).suffix.lstrip(".") or "png"
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{ext};base64,{b64}"}
                })
        HISTORY.append({"role": "user", "content": content_parts})
    else:
        HISTORY.append({"role": "user", "content": user_msg})

    generated_image = None

    for attempt in range(3):
        try:
            response_data = call_api_llm.call_chat_api(
                model=config.MODEL_NAME,
                messages=HISTORY,
                tools=ALL_TOOLS if attempt == 0 else None,
                stream=False
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            HISTORY.pop()
            return f"Lỗi: {str(e)}"

        msg = None
        if "message" in response_data:
            msg = response_data["message"]
        elif "choices" in response_data and response_data["choices"]:
            msg = response_data["choices"][0].get("message", {})

        if not msg:
            HISTORY.pop()
            return "Không thể lấy phản hồi từ API."

        tool_calls = msg.get("tool_calls")

        if not tool_calls:
            content = msg.get("content", "")
            if content:
                HISTORY.append({"role": "assistant", "content": content})
            if len(HISTORY) > config.MAX_TOKEN_CHAT // 2:
                HISTORY[:] = [HISTORY[0]] + HISTORY[-(config.MAX_TOKEN_CHAT // 2 - 1):]
            _save_history()

            if generated_image:
                return {"text": content, "images": generated_image}
            return content

        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name")
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}

            args["_user_id"] = user_id
            result_text, img_path = _execute_tool(name, args)
            if img_path:
                generated_image = img_path

            result_str = str(result_text) if not isinstance(result_text, str) else result_text
            HISTORY.append({
                "role": "system",
                "content": f"[TOOL_RESULT] {name}: {result_str}"
            })

    HISTORY.pop()
    return "Quá số lần thử xử lý."
