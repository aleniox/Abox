from typing import List, Dict
import json
import os
from pathlib import Path

# Memory paths - sử dụng storage directory
MEMORY_DIR = Path("storage") / "memory"
CHAT_HISTORY_FILE = MEMORY_DIR / "chat_history.json"
KNOWLEDGE_FILE = MEMORY_DIR / "knowledge.md"

# Ensure memory directory exists
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

MAX_HISTORY_TURNS = 10  # Mỗi turn = user + assistant

def trim_history(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    # """Giới hạn số lượt trò chuyện trong lịch sử."""
    system = history[:1]
    turns = history[1:]
    return system + turns[-MAX_HISTORY_TURNS * 2:]


# ============= CHAT HISTORY MANAGEMENT (JSON) =============

def load_chat_history() -> List[Dict[str, str]]:
    """Load chat history from JSON file"""
    if CHAT_HISTORY_FILE.exists():
        try:
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Lỗi khi đọc chat history: {e}")
            return []
    return []


def save_chat_history(history: List[Dict[str, str]]) -> None:
    """Save chat history to JSON file"""
    try:
        with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Lỗi khi lưu chat history: {e}")


def load_knowledge() -> str:
    """Load knowledge base from Markdown file"""
    if KNOWLEDGE_FILE.exists():
        try:
            with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"⚠️ Lỗi khi đọc knowledge base: {e}")
            return ""
    return ""


def save_knowledge(content: str) -> None:
    """Save knowledge base to Markdown file"""
    try:
        with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"❌ Lỗi khi lưu knowledge base: {e}")


def add_knowledge(section_title: str, content: str) -> None:
    """Add or update a section in the knowledge base"""
    knowledge = load_knowledge()
    
    # If section already exists, replace it
    if f"## {section_title}" in knowledge:
        parts = knowledge.split(f"## {section_title}")
        before = parts[0]
        after_parts = parts[1].split("\n## ")
        after = "\n## ".join(after_parts[1:]) if len(after_parts) > 1 else ""
        
        new_knowledge = before + f"## {section_title}\n{content}\n\n" + after
    else:
        # Add as new section
        new_knowledge = knowledge + f"\n## {section_title}\n{content}\n\n"
    
    save_knowledge(new_knowledge)


# Initialize memory files if they don't exist
if not CHAT_HISTORY_FILE.exists():
    save_chat_history([])

if not KNOWLEDGE_FILE.exists():
    save_knowledge("""# Knowledge Base

This knowledge base stores information for the chatbot to reference during conversations.

## Template
- Add sections as needed using markdown headers.
- Keep information organized and easily accessible.
""")