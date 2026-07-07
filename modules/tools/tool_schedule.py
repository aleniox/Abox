import json
import os
import uuid
from datetime import datetime

import pandas as pd
import pytz

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")

SCHEDULE_FILE = "storage/schedules/schedules.json"
SCHEDULE_XLSX_FILE = "storage/schedules/schedules.xlsx"

PENDING_KEY = "pending_schedule"


def _ensure_file():
    os.makedirs(os.path.dirname(SCHEDULE_FILE), exist_ok=True)
    if not os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_schedules():
    _ensure_file()
    try:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_schedules_to_xlsx(schedules):
    if not schedules:
        return
    try:
        rows = []
        for s in schedules:
            action = s.get("action", {})
            rows.append({
                "ID": s["id"],
                "User ID": s["user_id"],
                "Tiêu đề": s["title"],
                "Giờ": f"{int(s['hour']):02d}:{int(s['minute']):02d}",
                "Loại": "Hàng ngày" if s["type"] == "daily" else "Một lần",
                "Hành động": "Nhắc nhở" if action.get("type") == "reminder" else "Crawl web" if action.get("type") == "web_scrape" else "Tác vụ tự động",
                "URL": action.get("url", ""),
                "Hướng dẫn": action.get("instruction", "") or action.get("prompt", ""),
                "Kích hoạt": "Có" if s.get("enabled", True) else "Không",
                "Tạo lúc": s.get("created_at", "")
            })
        df = pd.DataFrame(rows)
        os.makedirs(os.path.dirname(SCHEDULE_XLSX_FILE), exist_ok=True)
        df.to_excel(SCHEDULE_XLSX_FILE, index=False, sheet_name="Lịch nhắc nhở")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Lỗi khi lưu Excel: {e}")


def save_schedules(schedules):
    _ensure_file()
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(schedules, f, ensure_ascii=False, indent=2)
    save_schedules_to_xlsx(schedules)


def add_schedule(user_id, title, hour, minute, type_, action, platform="discord"):
    schedules = load_schedules()
    try:
        hour = int(hour)
    except (TypeError, ValueError):
        hour = 0
    try:
        minute = int(minute)
    except (TypeError, ValueError):
        minute = 0
    sched = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "platform": platform,
        "title": title,
        "hour": hour,
        "minute": minute,
        "type": type_,
        "action": action,
        "enabled": True,
        "created_at": datetime.now(VN_TZ).isoformat()
    }
    schedules.append(sched)
    save_schedules(schedules)
    return sched


def delete_schedule(schedule_id):
    schedules = load_schedules()
    schedules = [s for s in schedules if s["id"] != schedule_id]
    save_schedules(schedules)
    return True


def list_schedules(user_id):
    return [s for s in load_schedules() if s["user_id"] == user_id and s["enabled"]]


def get_due_schedules(hour, minute, platform=None):
    all_sched = load_schedules()
    result = []
    for s in all_sched:
        if not s.get("enabled"):
            continue
        if s["hour"] == hour and s["minute"] == minute:
            if platform is None or s.get("platform", "discord") == platform:
                result.append(s)
    return result


def get_missed_once_schedules(minutes_back: int = 5):
    schedules = load_schedules()
    now = datetime.now(VN_TZ)
    missed = []
    for s in schedules:
        if not s.get("enabled") or s.get("type") != "once":
            continue
        created = s.get("created_at")
        if not created:
            continue
        try:
            created_dt = datetime.fromisoformat(created)
            if created_dt.tzinfo is None:
                created_dt = VN_TZ.localize(created_dt)
        except Exception:
            continue
        sched_time = created_dt.replace(hour=s["hour"], minute=s["minute"], second=0, microsecond=0)
        diff = (now - sched_time).total_seconds()
        if 0 <= diff <= minutes_back * 60:
            missed.append(s)
    return missed


schedule_tool_def = {
    "type": "function",
    "function": {
        "name": "schedule_reminder",
        "description": "Quản lý lịch nhắc nhở: thêm, xem, xóa lịch. Khi user yêu cầu thêm lịch, gọi action='add' để parse thông tin. Sau đó show preview và hỏi xác nhận. CHỈ gọi confirm_add khi user đã xác nhận.",
        "parameters": {
            "type": "object",
            "required": ["action", "hour", "minute"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "confirm_add", "cancel_add", "list", "delete"],
                    "description": "'add': parse yêu cầu và trả pending\n'confirm_add': lưu schedule đã pending vào file\n'cancel_add': hủy pending\n'list': xem danh sách lịch\n'delete': xóa lịch"
                },
                "title": {
                    "type": "string",
                    "description": "Tiêu đề lịch nhắc nhở"
                },
                "hour": {
                    "type": "integer",
                    "description": "Giờ (0-23)"
                },
                "minute": {
                    "type": "integer",
                    "description": "Phút (0-59)"
                },
                "type": {
                    "type": "string",
                    "enum": ["daily", "once"],
                    "description": "'daily': lặp lại mỗi ngày, 'once': một lần"
                },
                "action_type": {
                    "type": "string",
                    "enum": ["reminder", "web_scrape", "auto_action"],
                    "description": "'reminder': nhắc nhở text\n'web_scrape': crawl web và báo cáo\n'auto_action': tự động chạy script"
                },
                "url": {
                    "type": "string",
                    "description": "URL cần crawl (chỉ dùng khi action_type='web_scrape')"
                },
                "instruction": {
                    "type": "string",
                    "description": "Hướng dẫn tóm tắt nội dung"
                },
                "prompt": {
                    "type": "string",
                    "description": "Prompt tùy chỉnh cho auto_action"
                },
                "schedule_id": {
                    "type": "string",
                    "description": "ID lịch cần xóa (dùng cho delete)"
                },
                "platform": {
                    "type": "string",
                    "enum": ["discord", "telegram"],
                    "description": "Nền tảng: discord hoặc telegram (mặc định discord)"
                }
            }
        }
    }
}


def handle_schedule_tool(args, user_id):
    action = args.get("action")

    if action == "add":
        title = args.get("title", "")
        hour = args.get("hour")
        minute = args.get("minute")
        type_ = args.get("type", "daily")
        atype = args.get("action_type", "reminder")
        url = args.get("url", "")
        instruction = args.get("instruction", "")
        prompt = args.get("prompt", "")
        platform = args.get("platform", "discord")
        return f"PARSED | title={title} | hour={hour} | minute={minute} | type={type_} | action_type={atype} | url={url} | instruction={instruction} | prompt={prompt} | platform={platform} | pending"

    elif action == "confirm_add":
        platform = args.get("platform", "discord")
        sched = add_schedule(
            user_id=user_id,
            title=args.get("title", "Nhắc nhở"),
            hour=args.get("hour", 12),
            minute=args.get("minute", 0),
            type_=args.get("type", "daily"),
            action={
                "type": args.get("action_type", "reminder"),
                "url": args.get("url", ""),
                "instruction": args.get("instruction", ""),
                "prompt": args.get("prompt", "")
            },
            platform=platform
        )
        return f"✅ Đã lưu lịch nhắc nhở **{sched['title']}** lúc {sched['hour']:02d}:{sched['minute']:02d} ({sched['type']})."

    elif action == "cancel_add":
        return "❌ Đã hủy, không lưu lịch nào."

    elif action == "list":
        schedules = list_schedules(user_id)
        if not schedules:
            return "📭 Bạn chưa có lịch nhắc nhở nào."
        lines = [f"📋 **Danh sách lịch nhắc nhở:**"]
        for s in schedules:
            atype = "🔔 Nhắc" if s["action"]["type"] == "reminder" else "🌐 Crawl"
            lines.append(f"• `{s['id'][:8]}...` {atype} **{s['title']}** lúc {s['hour']:02d}:{s['minute']:02d} ({s['type']})")
        return "\n".join(lines)

    elif action == "delete":
        sid = args.get("schedule_id")
        if not sid:
            return "⚠️ Vui lòng cung cấp schedule_id."
        schedules = load_schedules()
        found = None
        for s in schedules:
            if s["id"] == sid and s["user_id"] == user_id:
                found = s
                break
            if s["id"].startswith(sid) and s["user_id"] == user_id:
                found = s
                break
        if not found:
            return "⚠️ Không tìm thấy lịch với ID này."
        delete_schedule(found["id"])
        return f"✅ Đã xóa lịch **{found['title']}**."

    return "⚠️ Action không hợp lệ."


def _safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        import sys
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()


def execute_due_schedules(report_func=_safe_print, platform=None):
    """
    Kiểm tra và thực thi các schedule đến giờ.
    report_func: callback nhận text
    platform: lọc theo nền tảng ("discord", "telegram", None = tất cả)
    Trả về số lượng schedule đã xử lý.
    """
    now = datetime.now(VN_TZ)
    due = get_due_schedules(now.hour, now.minute, platform=platform)
    count = 0

    for sched in due:
        action = sched.get("action", {})
        atype = action.get("type", "reminder")

        try:
            if atype == "reminder":
                report_func(f"⏰ **Nhắc nhở:** {sched['title']}")
                count += 1

            elif atype == "web_scrape":
                url = action.get("url", "")
                instruction = action.get("instruction", "Tóm tắt nội dung")
                report_func(f"🔄 Đang xử lý lịch **{sched['title']}** — crawl {url}...")

                from modules.tools.tool_searchs import web_crawl_data
                docs = web_crawl_data([url])
                raw_text = " ".join(d.page_content for d in docs)
                if len(raw_text) > 8000:
                    raw_text = raw_text[:8000]

                summary_prompt = f"{instruction}\n\nNội dung:\n{raw_text}"
                from modules.core.call_api_llm import call_chat_api
                import modules.config.config as cfg
                resp = call_chat_api(
                    model=cfg.MODEL_NAME,
                    messages=[{"role": "user", "content": summary_prompt}],
                    stream=False
                )
                summary = ""
                if "message" in resp:
                    summary = resp["message"].get("content", "")
                elif "choices" in resp and resp["choices"]:
                    summary = resp["choices"][0].get("message", {}).get("content", "")

                report_func(f"📊 **Báo cáo {sched['title']}:**\n{summary[:2000]}")
                count += 1
        except Exception as e:
            import traceback
            traceback.print_exc()
            report_func(f"[ERROR] Lỗi khi xử lý {sched['title']}: {str(e)[:200]}")

        if sched.get("type") == "once":
            delete_schedule(sched["id"])

    return count


def get_due_reports(platform="discord"):
    """
    Lấy danh sách (user_id, text) cho các schedule đến giờ.
    Xử lý luôn web_scrape (crawl + summarize) và xóa once.
    """
    now = datetime.now(VN_TZ)
    due = get_due_schedules(now.hour, now.minute, platform=platform)
    reports = []

    for sched in due:
        action = sched.get("action", {})
        atype = action.get("type", "reminder")
        text = ""

        try:
            if atype == "reminder":
                text = f"⏰ **Nhắc nhở:** {sched['title']}"

            elif atype == "web_scrape":
                url = action.get("url", "")
                instruction = action.get("instruction", "Tóm tắt nội dung")
                from modules.tools.tool_searchs import web_crawl_data
                docs = web_crawl_data([url])
                raw_text = " ".join(d.page_content for d in docs)
                if len(raw_text) > 8000:
                    raw_text = raw_text[:8000]

                summary_prompt = f"{instruction}\n\nNội dung:\n{raw_text}"
                from modules.core.call_api_llm import call_chat_api
                import modules.config.config as cfg
                resp = call_chat_api(
                    model=cfg.MODEL_NAME,
                    messages=[{"role": "user", "content": summary_prompt}],
                    stream=False
                )
                summary = ""
                if "message" in resp:
                    summary = resp["message"].get("content", "")
                elif "choices" in resp and resp["choices"]:
                    summary = resp["choices"][0].get("message", {}).get("content", "")

                text = f"📊 **Báo cáo {sched['title']}:**\n{summary[:2000]}"
        except Exception as e:
            text = f"[ERROR] Lỗi khi xử lý {sched['title']}: {str(e)[:200]}"

        if text:
            reports.append((sched["user_id"], text))

        if sched.get("type") == "once":
            delete_schedule(sched["id"])

    return reports
