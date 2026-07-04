import json
import os
import uuid
from datetime import datetime

import pytz

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")

SCHEDULE_FILE = "storage/schedules/schedules.json"

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


def save_schedules(schedules):
    _ensure_file()
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(schedules, f, ensure_ascii=False, indent=2)


def add_schedule(user_id, title, hour, minute, type_, action):
    schedules = load_schedules()
    try:
        hour = int(hour)
    except (TypeError, ValueError):
        hour = 0
    else:
        hour = max(0, min(23, hour))
    try:
        minute = int(minute)
    except (TypeError, ValueError):
        minute = 0
    else:
        minute = max(0, min(59, minute))
    sched = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
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


def get_due_schedules(hour, minute):
    return [s for s in load_schedules()
            if s["enabled"] and s["hour"] == hour and s["minute"] == minute]


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


def handle_schedule_tool(args, user_id):
    action = args.get("action")

    if action == "add":
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
            }
        )
        return f"✅ Đã lưu lịch nhắc nhở **{sched['title']}** lúc {sched['hour']:02d}:{sched['minute']:02d} ({sched['type']})."

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


def execute_due_schedules(report_func=_safe_print):
    """
    Kiểm tra và thực thi các schedule đến giờ.
    report_func: callback nhận text để hiển thị (print cho CLI, send_message cho Discord)
    Trả về số lượng schedule đã xử lý.
    """
    now = datetime.now(VN_TZ)
    due = get_due_schedules(now.hour, now.minute)
    count = 0

    for sched in due:
        if not sched.get("enabled", True):
            continue

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
