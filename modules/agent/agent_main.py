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
from modules.tools.tool_searchs import web_search, web_crawl_data
from modules.tools.tool_generate import call_api_generate_image
from modules.tools.tool_expense import handle_expense_tool

logger = logging.getLogger(__name__)

# --- Paths ---
PERSONALITY_PROMPT_FILE = Path(__file__).parent.parent.parent / "storage" / "prompts" / "personality_prompt.md"
PROFILE_DIR = Path("storage/profiles")
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

# --- Personality (dùng cho Responder) ---
def _load_personality() -> str:
    if PERSONALITY_PROMPT_FILE.exists():
        try:
            return PERSONALITY_PROMPT_FILE.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Loi doc personality prompt: {e}")
    return "You are a helpful AI assistant."

BASE_SYSTEM = _load_personality()

RESPONDER_INSTRUCTION = """

Ban nhan duoc [BRAIN_RESULT] tu bo nao xu ly tools.
Nhiet vu: lay [BRAIN_RESULT], viet lai bang giong noi ca tinh cua ban, tra loi truc tiep vao cau hoi cua nguoi dung.
KHONG hien thi [BRAIN_RESULT] hay [TOOL_RESULT] hay bat ky mark noi bo nao cho user thay."""

# --- User profile ---
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
    "url_search", "generate_image", "generate_voice", "expense_tracker"
}

BRAIN_SYSTEM = """<brain>
  <mission>
    Bạn là bộ não xử lý công cụ. Phân tích yêu cầu người dùng, dựa vào ngữ cảnh các hành động đã thực hiện, quyết định hành động tiếp theo.
    Đầu ra là JSON với cấu trúc: {"input": "", "next_action": "", "reason": "", "parameters": {}}
    Nếu có <task_context> ở cuối tin nhắn: đây là tác vụ tự động theo lịch trình, KHÔNG phải tin nhắn từ người dùng. BẮT BUỘC dùng công cụ (search_web, url_search) để lấy dữ liệu mới nhất. KHÔNG output answer khi chưa gọi tool nào. KHÔNG hỏi lại người dùng.
  </mission>
  <context>
    Lịch sử các hành động đã thực hiện trong phiên này. Dựa vào đây để quyết định next_action phù hợp.
  </context>
  <context_rules>
    - Nếu ngữ cảnh có entry schedule_reminder với kết quả chứa "pending" và action_type="agent_task" -> confirm_add NGAY, không hỏi
    - Nếu ngữ cảnh có entry schedule_reminder với kết quả chứa "pending" và người dùng xác nhận (ok/yes/đồng ý/có/ừ) -> next_action=schedule_reminder, input=confirm_add
    - Nếu ngữ cảnh có entry pending và người dùng sửa -> next_action=schedule_reminder, input=add với thông tin mới
    - Nếu ngữ cảnh có entry pending và người dùng từ chối -> next_action=schedule_reminder, input=cancel_add
  </context_rules>
  <task_rules>
    - Sau mỗi lần gọi search_web: nếu kết quả chưa đủ thông tin, thiếu số liệu cụ thể, hoặc quá chung chung -> thử lại với từ khoá khác cụ thể hơn
    - Nếu search_web trả về các URL/nguồn có vẻ liên quan -> dùng url_search để đọc nội dung chi tiết từ các URL đó
    - Có thể gọi search_web và url_search nhiều lần để lấy dữ liệu từ nhiều nguồn khác nhau
    - Chỉ output answer khi đã có đủ dữ liệu để trả lời. Không dừng sớm.
  </task_rules>
  <tools>
    <tool name="schedule_reminder">
      <input>add|confirm_add|cancel_add|list|delete</input>
      <parameters>
        <param name="title" required="add,confirm_add">Tiêu đề lịch</param>
        <param name="hour" required="add,confirm_add">Giờ (0-23)</param>
        <param name="minute" required="add,confirm_add">Phút (0-59)</param>
        <param name="type" required="add,confirm_add">"daily" hoặc "once"</param>
        <param name="action_type" required="add">"reminder" (nhắc text) hoặc "agent_task" (báo cáo tự động)</param>
        <param name="prompt" required="agent_task">Yêu cầu chi tiết agent sẽ thực thi khi đến giờ</param>
        <param name="schedule_id" required="delete">ID lịch cần xoá</param>
      </parameters>
    </tool>
    <tool name="calculus_calculator">
      <input>calculate|derivative|integral</input>
      <parameters>
        <param name="expression" required="all">Biểu thức toán học</param>
        <param name="variable" optional="all">Biến số (mặc định x)</param>
        <param name="lower_bound" optional="integral">Cận dưới</param>
        <param name="upper_bound" optional="integral">Cận trên</param>
      </parameters>
    </tool>
    <tool name="search_web">
      <input>search</input>
      <parameters>
        <param name="query" required="search">Từ khoá tìm kiếm</param>
      </parameters>
    </tool>
    <tool name="url_search">
      <input>fetch</input>
      <parameters>
        <param name="url" required="fetch">URL cần đọc</param>
      </parameters>
    </tool>
    <tool name="generate_image">
      <input>generate</input>
      <parameters>
        <param name="prompt" required="generate">Mô tả ảnh cần tạo</param>
      </parameters>
    </tool>
    <tool name="generate_voice">
      <input>generate</input>
      <parameters>
        <param name="text" required="generate">Nội dung cần đọc</param>
      </parameters>
    </tool>
    <tool name="expense_tracker">
      <input>add|list|delete</input>
      <parameters>
        <param name="amount" required="add">Số tiền</param>
        <param name="category" required="add">Danh mục (food/transport/entertainment/other)</param>
        <param name="note" optional="add">Ghi chú</param>
        <param name="expense_id" required="delete">ID chi tiêu cần xoá</param>
      </parameters>
    </tool>
  </tools>
  <schedule_rules>
    <step number="1">Người dùng yêu cầu thêm lịch -> input=add, next_action=schedule_reminder với đầy đủ title/hour/minute/type/action_type</step>
    <step number="1b">Người dùng yêu cầu báo cáo định kỳ vào giờ cố định -> input=add, action_type=agent_task, prompt mô tả chi tiết công việc agent cần làm khi đến giờ</step>
    <step number="1c">Nếu action_type="agent_task": sau khi add trả pending -> gọi confirm_add NGAY (bỏ qua bước hỏi xác nhận). Không output answer.</step>
    <step number="1.5">Nếu action_type="reminder": SAU KHI tool trả về "pending": ngay lập tức output next_action="answer" — KHÔNG tự động confirm_add. Đợi người dùng xác nhận ở message tiếp theo.</step>
    <step number="2">Người dùng xác nhận (message riêng, nói "ok/yes/đồng ý/có/ừ") -> input=confirm_add, next_action=schedule_reminder. LẤY title/hour/minute/action_type/prompt từ kết quả (result) của entry pending trong ngữ cảnh.</step>
    <warning>KHÔNG tự động gọi confirm_add sau khi nhận pending (ngoại trừ agent_task). Luôn phải dừng lại và hỏi người dùng trước.</warning>
    <warning>confirm_add CHỈ được gọi khi người dùng chủ động xác nhận ở một message hoàn toàn riêng biệt, hoặc action_type là agent_task.</warning>
  </schedule_rules>
  <output_logic>
    - next_action="answer": dừng vòng lặp. input là nội dung trả về cuối cùng.
      NẾU đã gọi tool: input mô tả ngắn gọn những gì đã làm và cần người dùng làm gì tiếp theo (vd: "Đã phân tích lịch 'Đi ngủ' 0h23 hằng ngày. Người dùng cần xác nhận.")
      NẾU không gọi tool: input là câu trả lời trực tiếp
    - next_action=tên_công_cụ: mã sẽ gọi công cụ tương ứng. input là hành động của công cụ đó. parameters là tham số.
    - LUÔN đặt next_action. KHÔNG bao giờ để trống.
  </output_logic>
</brain>"""

# Track context entries for each user (persists across messages)
CONTEXT: Dict[int, List[Dict]] = {}


def _encode_image(image_path: Path) -> Optional[str]:
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Loi encode anh {image_path}: {e}")
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
        logger.warning(f"[BRAIN] next_action khong hop le: {next_action}")
        return None
    return data


def _wrap_brain_output(tools_called: bool, tool_name: str, tool_result: str, fallback: str) -> str:
    if tools_called and tool_name:
        return f"[Ket qua tu tool {tool_name}]: {tool_result}"
    return fallback


def _execute_tool(tool_name: str, action: str, params: dict, user_id: int) -> Tuple[str, Optional[str]]:
    generated_image = None
    logger.info(f"[TOOL] Goi tool: {tool_name} | input={action} | params={json.dumps(params, ensure_ascii=False)[:200]}")

    all_args = {**params, "_user_id": user_id}

    try:
        if tool_name == "schedule_reminder":
            all_args["action"] = action
            result = handle_schedule_tool(all_args, user_id)

        elif tool_name == "calculus_calculator":
            result = calculus_calculator(
                expression=params.get("expression"), operation=params.get("operation", action),
                evaluate=params.get("evaluate"), variable=params.get("variable"),
                lower_bound=params.get("lower_bound"), upper_bound=params.get("upper_bound"))

        elif tool_name == "search_web":
            contexts = web_search(query=params.get("query", ""))
            result = contexts[1]

        elif tool_name == "url_search":
            docs = web_crawl_data(url_doc=params.get("url", ""))
            result = '\n'.join(
                f"Source: {doc.metadata.get('source')}, Title: {doc.metadata.get('title')}, "
                f"Language: {doc.metadata.get('language', 'None')}, "
                f"Page_content: {clean_excessive_newlines(doc.page_content)}"
                for doc in docs)

        elif tool_name == "generate_image":
            img_path = call_api_generate_image(params)
            generated_image = img_path
            result = f"Da tao anh va luu tai {img_path}"

        elif tool_name == "generate_voice":
            result = f"Da tao giong noi cho: {params.get('text', '')}"

        elif tool_name == "expense_tracker":
            all_args["action"] = action
            result = handle_expense_tool(args=all_args)

        else:
            result = f"Tool khong ho tro: {tool_name}"

    except Exception as e:
        import traceback
        traceback.print_exc()
        result = f"Loi khi chay tool {tool_name}: {str(e)}"

    result_str = str(result)
    logger.info(f"[TOOL] Ket qua: {result_str[:200]}")

    # Save to CONTEXT
    CONTEXT.setdefault(user_id, []).append({
        "tool": tool_name,
        "action": action,
        "result": result_str[:500],
        "time": datetime.now().isoformat()
    })

    return result_str, generated_image


def _brain_process(user_message: str, user_id: int,
                   image_paths: Optional[List[Path]] = None,
                   context_str: str = "",
                   task_context: str = "") -> Tuple[str, Optional[str]]:
    logger.info(f"[BRAIN] === START === user_id={user_id} | message={user_message[:100]} | images={len(image_paths or [])}")

    system_content = BRAIN_SYSTEM
    if context_str:
        system_content += "\n\n" + context_str
        logger.info(f"[BRAIN] Co context ({len(context_str)} chars)")
    if task_context:
        system_content += "\n\n" + task_context
        logger.info(f"[BRAIN] Co task_context ({len(task_context)} chars)")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"[{now}] (user_id={user_id}) {user_message.strip()}"

    if image_paths:
        content_parts = [{"type": "text", "text": content}]
        for img_path in image_paths:
            b64 = _encode_image(img_path)
            if b64:
                ext = Path(img_path).suffix.lstrip(".") or "png"
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{ext};base64,{b64}"}
                })
        messages = [{"role": "system", "content": system_content},
                    {"role": "user", "content": content_parts}]
    else:
        messages = [{"role": "system", "content": system_content},
                    {"role": "user", "content": content}]

    generated_image = None
    tools_called = False
    last_tool_name = ""
    last_tool_result = ""
    prev_calls: List[Tuple[str, str]] = []  # (tool_name, input) để phát hiện lặp

    for attempt in range(3):
        logger.info(f"[BRAIN] Attempt {attempt + 1}/3 — goi LLM")
        try:
            data = call_api_llm.call_chat_api(
                model=config.MODEL_NAME, messages=messages, stream=False)
            finish = data.get('choices', [{}])[0].get('finish_reason', '?') if 'choices' in data else '?'
            logger.info(f"[BRAIN] LLM tra ve: finish_reason={finish}")
            logger.info(f"[BRAIN] LLM tra ve: finish_reason={data}")

        except Exception as e:
            logger.error(f"[BRAIN] LLM call failed: {e}")
            return _wrap_brain_output(tools_called, last_tool_name, last_tool_result, f"Loi: {str(e)}"), None

        msg = data.get("message") or (data.get("choices", [{}])[0].get("message", {}) if "choices" in data else None)
        if not msg:
            logger.warning("[BRAIN] Khong lay duoc message tu response")
            return _wrap_brain_output(tools_called, last_tool_name, last_tool_result, "Khong the lay phan hoi tu API."), None

        raw_text = msg.get("content", "").strip()
        parsed = _parse_tool_json(raw_text)

        if not parsed:
            # Not valid JSON — treat as raw answer text
            logger.info(f"[BRAIN] Khong phai JSON, tra ve raw text ({len(raw_text)} chars)")
            return _wrap_brain_output(tools_called, last_tool_name, last_tool_result, raw_text), generated_image

        next_action = parsed.get("next_action", "")

        if next_action == "answer":
            answer_text = parsed.get("input", "") or parsed.get("reason", "") or raw_text
            logger.info(f"[BRAIN] Nhan answer, input={answer_text[:100]}")
            return answer_text, generated_image

        if not next_action:
            logger.warning("[BRAIN] next_action trong, khong hop le")
            return _wrap_brain_output(tools_called, last_tool_name, last_tool_result, raw_text), generated_image

        # Execute tool
        input_val = parsed.get("input", "")
        parameters = parsed.get("parameters", {})
        result_text, img_path = _execute_tool(next_action, input_val, parameters, user_id)
        if img_path:
            generated_image = img_path
        tools_called = True
        last_tool_name = next_action
        last_tool_result = result_text

        # Phát hiện lặp: nếu tool+input giống hệt lần trước -> dừng
        call_key = (next_action, input_val)
        if prev_calls and prev_calls[-1] == call_key:
            logger.warning(f"[BRAIN] Phat hien lap tool {next_action}/{input_val}, dung loop")
            return _wrap_brain_output(tools_called, last_tool_name, last_tool_result, f"[Ket qua tu tool {next_action}]: {result_text}"), generated_image
        prev_calls.append(call_key)

        # Add result to messages for next iteration
        messages.append({"role": "system", "content": f"[TOOL_RESULT] {next_action}: {result_text}"})

    logger.warning("[BRAIN] Het 3 lan thu, tra ve fallback")
    return _wrap_brain_output(tools_called, last_tool_name, last_tool_result, "Qua so lan xu ly."), generated_image


# ============================================================
#  RESPONDER — Personality styling (có history)
# ============================================================

HISTORY: List[Dict] = []


def _load_history(user_id: int):
    global HISTORY
    profile = _load_user_profile(user_id)
    prompt = BASE_SYSTEM
    if profile.get("name"):
        prompt += f"\n\nNguoi dung cua ban ten la {profile['name']}."
    prefs = profile.get("preferences", {})
    if prefs.get("habits"):
        prompt += f"\nThoi quen: {', '.join(prefs['habits'])}."
    if prefs.get("interests"):
        prompt += f"\nSo thich: {', '.join(prefs['interests'])}."

    raw = memory.load_chat_history()
    full_prompt = prompt + RESPONDER_INSTRUCTION
    HISTORY = [{"role": "system", "content": full_prompt}] + raw[1:] if raw else [{"role": "system", "content": full_prompt}]


def _save_history():
    memory.save_chat_history(HISTORY[1:])


def _responder_cycle(brain_result: str, user_id: int,
                     image_paths: Optional[List[Path]] = None,
                     original_message: str = "") -> str:
    logger.info(f"[RESPONDER] === START === user_id={user_id}")
    logger.info(f"[RESPONDER] Brain result ({len(brain_result)} chars): {brain_result[:150]}")
    _load_history(user_id)
    HISTORY.append({"role": "user", "content": original_message.strip()})
    HISTORY.append({"role": "system", "content": f"[BRAIN_RESULT] {brain_result}"})

    try:
        logger.info("[RESPONDER] Goi LLM de stylize cau tra loi...")
        data = call_api_llm.call_chat_api(
            model=config.MODEL_NAME, messages=HISTORY, stream=False)
    except Exception as e:
        logger.error(f"[RESPONDER] LLM call failed: {e}")
        HISTORY.pop()
        return f"Loi: {str(e)}"

    msg = data.get("message") or (data.get("choices", [{}])[0].get("message", {}) if "choices" in data else None)
    if not msg:
        logger.warning("[RESPONDER] Khong lay duoc message tu response")
        HISTORY.pop()
        return "Khong the lay phan hoi."

    content = msg.get("content", "")
    logger.info(f"[RESPONDER] Tra ve ({len(content)} chars): {content[:150]}")
    if content:
        HISTORY.append({"role": "assistant", "content": content})
    if len(HISTORY) > config.MAX_TOKEN_CHAT // 2:
        HISTORY[:] = [HISTORY[0]] + HISTORY[-(config.MAX_TOKEN_CHAT // 2 - 1):]
    _save_history()
    return content


# ============================================================
#  MAIN ENTRY POINT
# ============================================================

def process_message(message: str, user_id: int, channel=None,
                    image_paths: Optional[List[Path]] = None,
                    audio_paths: Optional[List[Path]] = None,
                    task_context: str = ""):
    if not message and not image_paths:
        logger.info("[MAIN] Bo qua: khong co message va khong co image")
        return None

    logger.info(f"[MAIN] === NHAN TIN NHAN === user_id={user_id} | {message[:100]} | images={len(image_paths or [])} | task_context={'co' if task_context else 'khong'}")

    # Phase 1: Brain (voi context tu cac hanh dong truoc)
    context = _get_recent_context(user_id)
    logger.info("[MAIN] Phase 1: BRAIN — bat dau xu ly tool...")
    brain_result, generated_image = _brain_process(message, user_id, image_paths, context_str=context, task_context=task_context)
    logger.info(f"[MAIN] Phase 1: BRAIN — ket qua: ({len(brain_result)} chars) {brain_result[:200]}")

    # Phase 2: Responder (bỏ qua nếu là task tự động — dùng brain_result trực tiếp)
    if task_context:
        logger.info("[MAIN] Task tu dong, bo qua Responder")
        if generated_image:
            return {"text": brain_result, "images": generated_image}
        return brain_result

    # Phase 2: Responder
    logger.info("[MAIN] Phase 2: RESPONDER — bat dau stylize...")
    final_response = _responder_cycle(brain_result, user_id, image_paths, original_message=message)
    logger.info(f"[MAIN] Phase 2: RESPONDER — hoan tat ({len(final_response)} chars)")

    if generated_image:
        logger.info(f"[MAIN] Tra ve text + image: {generated_image}")
        return {"text": final_response, "images": generated_image}

    logger.info("[MAIN] === KET THUC ===")
    return final_response
