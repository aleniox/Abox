import json
import logging
import base64
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from modules.core import call_api_llm
import modules.config.config as config
import modules.memory.memory as memory

from modules.tools.tool_schedule import handle_schedule_tool
from modules.tools.tools_call import calculus_calculator
from modules.tools.tool_searchs import web_search
from modules.tools.tool_generate import call_api_generate_image
from modules.tools.tool_expense import handle_expense_tool
from modules.tools.tool_crawl4ai import crawl_web

logger = logging.getLogger(__name__)

# --- Paths ---
PROMPT_DIR = Path(__file__).parent.parent.parent / "storage" / "prompts"
PERSONALITY_PROMPT_FILE = PROMPT_DIR / "personality_prompt.md"
BRAIN_PROMPT_FILE = PROMPT_DIR / "brain_system.md"
RESPONDER_INSTRUCTION_FILE = PROMPT_DIR / "responder_instruction.md"
PROFILE_DIR = Path("storage/profiles")
PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def _load_prompt(file_path: Path, default: str = "") -> str:
    if file_path.exists():
        try:
            return file_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning(f"Lỗi đọc prompt {file_path}: {e}")
    return default


BASE_SYSTEM = _load_prompt(PERSONALITY_PROMPT_FILE, default="You are a helpful AI assistant.")
_responder_content = _load_prompt(RESPONDER_INSTRUCTION_FILE)
RESPONDER_INSTRUCTION = f"\n\n{_responder_content}" if _responder_content else ""


def _load_user_profile(user_id: int) -> dict:
    profile_path = PROFILE_DIR / f"user_{user_id}.json"
    if profile_path.exists():
        try:
            return json.loads(profile_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"name": None, "preferences": {}, "created_at": datetime.now().isoformat()}


# ============================================================
#  BRAIN — Tool reasoning (stateless, no personality)
# ============================================================

VALID_TOOLS = {
    "schedule_reminder", "calculus_calculator", "search_web",
    "generate_image", "generate_voice", "expense_tracker", "crawl4ai"
}

BRAIN_SYSTEM = _load_prompt(BRAIN_PROMPT_FILE)

CONTEXT: Dict[int, List[Dict]] = {}
SEARCH_RESULTS: Dict[int, List[Dict]] = {}


def _encode_image(image_path: Path) -> Optional[str]:
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Lỗi encode ảnh {image_path}: {e}")
        return None


def clean_excessive_newlines(text: str) -> str:
    return re.sub(r'\n{3,}', '\n\n', text.strip())


def _get_recent_context(user_id: int) -> str:
    entries = CONTEXT.get(user_id, [])
    if not entries:
        return ""
    parts = ["<context>"]
    for e in entries[-5:]:
        tool = e.get("tool", "?")
        action = e.get("action", "?")
        result = (e.get("result", "") or "")[:200]
        parts.append(f'  <entry tool="{tool}" action="{action}">')
        parts.append(f"    {result}")
        parts.append("  </entry>")
    parts.append("</context>")
    return "\n".join(parts)


def _parse_tool_json(text: str) -> Optional[Dict]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?\s*```$', '', text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    next_action = data.get("next_action", "")
    if not next_action or next_action == "answer":
        return data
    if next_action not in VALID_TOOLS:
        logger.warning(f"[BRAIN] next_action không hợp lệ: {next_action}")
        return None
    return data


def _execute_tool(tool_name: str, action: str, params: dict, user_id: int, platform: str = "discord") -> Tuple[str, Optional[str]]:
    generated_image = None
    logger.info(f"[TOOL] Gọi tool: {tool_name} | input={action} | params={json.dumps(params, ensure_ascii=False)[:200]}")

    all_args = {**params, "_user_id": user_id}

    try:
        if tool_name == "schedule_reminder":
            if action not in ("add", "list", "delete"):
                action = "delete" if params.get("schedule_id") else "add"
            all_args["action"] = action
            all_args["platform"] = platform
            result = handle_schedule_tool(all_args, user_id)

        elif tool_name == "calculus_calculator":
            result = calculus_calculator(
                expression=params.get("expression"), operation=params.get("operation", action),
                evaluate=params.get("evaluate"), variable=params.get("variable"),
                lower_bound=params.get("lower_bound"), upper_bound=params.get("upper_bound"))

        elif tool_name == "search_web":
            query = params.get("query") or action or ""
            contexts = web_search(query=query)
            SEARCH_RESULTS[user_id] = contexts[0]
            result = contexts[1]

        elif tool_name == "generate_image":
            img_path = call_api_generate_image(params)
            generated_image = img_path
            result = f"Đã tạo ảnh và lưu tại {img_path}"

        # elif tool_name == "generate_voice":
        #     result = f"Đã tạo giọng nói cho: {params.get('text', '')}"

        elif tool_name == "expense_tracker":
            all_args["action"] = action
            result = handle_expense_tool(args=all_args)

        elif tool_name == "crawl4ai":
            raw_content = crawl_web(url=params.get("url", "") or action or "")
            result = clean_excessive_newlines(raw_content) if raw_content else "Không lấy được dữ liệu từ URL."
            SEARCH_RESULTS[user_id] = [{
                "url": params.get("url", "") or action or "",
                "title": f"Trang web: {params.get('url', '') or action or ''}",
                "description": result[:300]
            }]

        else:
            result = f"Tool không hỗ trợ: {tool_name}"

    except Exception as e:
        import traceback
        traceback.print_exc()
        result = f"Lỗi khi chạy tool {tool_name}: {str(e)}"

    result_str = str(result)
    logger.info(f"[TOOL] Kết quả: {result_str}")

    CONTEXT.setdefault(user_id, []).append({
        "tool": tool_name,
        "action": action,
        "result": result_str,
        "time": datetime.now().isoformat()
    })

    return result_str, generated_image


def _build_messages(system: str, user: str, images: list, results: str):
    sys_content = system
    if results:
        sys_content += "\n\n<running_results>\n" + results.strip()[-5000:] + "\n</running_results>"
    if images:
        parts = [{"type": "text", "text": user}]
        for img_path in images:
            b64 = _encode_image(img_path)
            if b64:
                ext = Path(img_path).suffix.lstrip(".") or "png"
                parts.append({"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}})
        return [{"role": "system", "content": sys_content}, {"role": "user", "content": parts}]
    return [{"role": "system", "content": sys_content}, {"role": "user", "content": user}]


def _brain_process(user_message: str, user_id: int,
                   image_paths: Optional[List[Path]] = None,
                   context_str: str = "",
                   task_context: str = "",
                   platform: str = "discord",
                   chat_history: Optional[List[Dict]] = None) -> Tuple[str, Optional[str]]:
    logger.info(f"[BRAIN] === START === user_id={user_id} | message={user_message[:100]} | images={len(image_paths or [])}")

    history_str = ""
    if chat_history:
        lines = []
        for m in chat_history[-6:]:
            role = m.get("role", "unknown")
            content = (m.get("content", "") or "")[:300]
            lines.append(f'<message role="{role}">\n{content}\n</message>')
        if lines:
            history_str = "\n".join(lines)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_content = BRAIN_SYSTEM.format(
        time=now_str, history=history_str, context=context_str or ""
    )
    if task_context:
        system_content += "\n\n" + task_context
        logger.info(f"[BRAIN] Có task_context ({len(task_context)} chars)")

    content = f"[{now_str}] (user_id={user_id}) {user_message.strip()}"

    generated_image = None
    tools_called = False
    last_tool_name = ""
    last_tool_result = ""
    prev_calls: List[Tuple[str, str]] = []
    running_results = ""

    def _brain_output(tools_called, tool_name, tool_result, fallback):
        return f"[Kết quả từ tool {tool_name}]: {tool_result}" if tools_called and tool_name else fallback

    messages = _build_messages(system_content, content, image_paths or [], running_results)

    for attempt in range(10):
        logger.info(f"[BRAIN] Attempt {attempt + 1}/10 — gọi LLM")
        try:
            data = call_api_llm.call_chat_api(
                model=config.MODEL_NAME, messages=messages, stream=False)
            logger.info(f"[BRAIN] LLM trả về: {data}")
        except Exception as e:
            logger.error(f"[BRAIN] LLM call failed: {e}")
            return _brain_output(tools_called, last_tool_name, last_tool_result, f"Lỗi: {str(e)}"), None

        msg = data.get("message") or (data.get("choices", [{}])[0].get("message", {}) if "choices" in data else None)
        if not msg:
            logger.warning("[BRAIN] Không lấy được message từ response")
            return _brain_output(tools_called, last_tool_name, last_tool_result, "Không thể lấy phản hồi từ API."), None

        raw_text = msg.get("content", "").strip()
        parsed = _parse_tool_json(raw_text)

        if not parsed:
            logger.info(f"[BRAIN] Không phải JSON, trả về raw text ({len(raw_text)} chars)")
            return _brain_output(tools_called, last_tool_name, last_tool_result, raw_text), generated_image

        next_action = parsed.get("next_action", "")

        if next_action == "answer":
            answer_text = parsed.get("output") or parsed.get("input") or parsed.get("reason") or raw_text
            logger.info(f"[BRAIN] Nhận answer, output={answer_text}")
            return answer_text, generated_image

        if not next_action:
            logger.warning("[BRAIN] next_action trống, không hợp lệ")
            return _brain_output(tools_called, last_tool_name, last_tool_result, raw_text), generated_image

        input_val = parsed.get("input", "")
        parameters = parsed.get("parameters", {})
        result_text, img_path = _execute_tool(next_action, input_val, parameters, user_id, platform=platform)
        if img_path:
            generated_image = img_path
        tools_called = True
        last_tool_name = next_action
        last_tool_result = result_text

        running_results += f'\n  <result tool="{next_action}" input="{input_val}">\n    {result_text}\n  </result>'
        messages = _build_messages(system_content, content, image_paths or [], running_results)

        call_key = (next_action, input_val)
        if prev_calls and prev_calls[-1] == call_key:
            logger.warning(f"[BRAIN] Phát hiện lặp tool {next_action}/{input_val}, dừng loop")
            return _brain_output(tools_called, last_tool_name, last_tool_result, f"[Kết quả từ tool {next_action}]: {result_text}"), generated_image
        prev_calls.append(call_key)

    logger.warning("[BRAIN] Hết 10 lần thử, trả về fallback")
    return _brain_output(tools_called, last_tool_name, last_tool_result, "Quá số lần xử lý."), generated_image


# ============================================================
#  RESPONDER — Personality styling (có history)
# ============================================================

HISTORY: List[Dict] = []


def _load_history(user_id: int, raw_history: Optional[List[Dict]] = None):
    global HISTORY
    profile = _load_user_profile(user_id)
    prompt = BASE_SYSTEM
    if profile.get("name"):
        prompt += f"\n\nNgười dùng của bạn tên là {profile['name']}."
    prefs = profile.get("preferences", {})
    if prefs.get("habits"):
        prompt += f"\nThói quen: {', '.join(prefs['habits'])}."
    if prefs.get("interests"):
        prompt += f"\nSở thích: {', '.join(prefs['interests'])}."

    raw = raw_history if raw_history is not None else memory.load_chat_history()
    full_prompt = prompt + RESPONDER_INSTRUCTION
    HISTORY = [{"role": "system", "content": full_prompt}] + raw[1:] if raw else [{"role": "system", "content": full_prompt}]


def _save_history():
    memory.save_chat_history(HISTORY[1:])


def _responder_cycle(brain_result: str, user_id: int,
                     image_paths: Optional[List[Path]] = None,
                     original_message: str = "",
                     raw_history: Optional[List[Dict]] = None) -> str:
    logger.info(f"[RESPONDER] === START === user_id={user_id}")
    logger.info(f"[RESPONDER] Brain result ({len(brain_result)} chars): {brain_result[:150]}")
    _load_history(user_id, raw_history)
    messages = HISTORY + [
        {"role": "system", "content": f"[BRAIN_RESULT] {brain_result}"},
        {"role": "user", "content": original_message.strip()}
    ]

    try:
        logger.info("[RESPONDER] Gọi LLM để stylize câu trả lời...")
        data = call_api_llm.call_chat_api(
            model=config.MODEL_NAME, messages=messages, stream=False)
    except Exception as e:
        logger.error(f"[RESPONDER] LLM call failed: {e}")
        return f"Lỗi: {str(e)}"

    msg = data.get("message") or (data.get("choices", [{}])[0].get("message", {}) if "choices" in data else None)
    if not msg:
        logger.warning("[RESPONDER] Không lấy được message từ response")
        return "Không thể lấy phản hồi."

    content = msg.get("content", "")
    logger.info(f"[RESPONDER] Trả về ({len(content)} chars): {content}")
    if content:
        HISTORY.append({"role": "user", "content": original_message.strip()})
        HISTORY.append({"role": "assistant", "content": content})
    _save_history()
    return content


# ============================================================
#  MAIN ENTRY POINT
# ============================================================

def process_message(message: str, user_id: int, channel=None,
                    image_paths: Optional[List[Path]] = None,
                    audio_paths: Optional[List[Path]] = None,
                    task_context: str = "",
                    platform: str = "discord"):
    if not message and not image_paths:
        logger.info("[MAIN] Bỏ qua: không có message và không có image")
        return None

    logger.info(f"[MAIN] === NHẬN TIN NHẮN === user_id={user_id} | {message[:100]} | images={len(image_paths or [])} | task_context={'có' if task_context else 'không'}")

    chat_history = memory.load_chat_history()
    context = _get_recent_context(user_id)

    logger.info("[MAIN] Phase 1: BRAIN — bắt đầu xử lý tool...")
    brain_result, generated_image = _brain_process(
        message, user_id, image_paths, context_str=context,
        task_context=task_context, platform=platform, chat_history=chat_history)
    logger.info(f"[MAIN] Phase 1: BRAIN — kết quả: ({len(brain_result)} chars) {brain_result[:200]}")

    if task_context:
        logger.info("[MAIN] Task tự động, bỏ qua Responder")
        return {"text": brain_result, "images": generated_image} if generated_image else brain_result

    logger.info("[MAIN] Phase 2: RESPONDER — bắt đầu stylize...")
    final_response = _responder_cycle(brain_result, user_id, image_paths, original_message=message, raw_history=chat_history)
    logger.info(f"[MAIN] Phase 2: RESPONDER — hoàn tất ({len(final_response)} chars)")

    if generated_image:
        logger.info(f"[MAIN] Trả về text + image: {generated_image}")
        return {"text": final_response, "images": generated_image}

    logger.info("[MAIN] === KẾT THÚC ===")
    return final_response
