# test_agent_cli.py
import sys, os
sys.path.insert(0, "D:\\Abox")
os.chdir("D:\\Abox")
sys.stdout = open(1, "w", encoding="utf-8", closefd=False)

from modules.agent import agent_main

USER_ID = 123456789

print("=" * 60)
print("  Schedule Agent CLI Test")
print("  Nhập câu tự nhiên, agent tự chọn tool qua LLM")
print("  VD: nhắc ăn cơm 12h hằng ngày")
print("  VD: xem lịch của tôi")
print("  VD: xóa lịch ...")
print("  Gõ 'exit' để thoát")
print("=" * 60)

while True:
    try:
        msg = input("\nYou: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nBye!")
        break

    if msg.lower() in ("exit", "quit"):
        print("Bye!")
        break
    if not msg:
        continue

    response = agent_main.process_message(msg, USER_ID)
    print(f"Bot: {response}")
    print(f"  [History: {len(agent_main.HISTORY)} messages]")