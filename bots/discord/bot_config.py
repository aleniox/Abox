"""
Bot configuration and constants
"""
from datetime import time as dt_time
import pytz
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Timezone
VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")

# Environment variables
TOKEN = os.getenv("DISCORD_TOK")
USER_ID = int(os.getenv("USER_ID")) if os.getenv("USER_ID") else None

# Connection retry settings
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds
SETTIMER = 30

# Check-in Configuration
CHECKIN_CONFIG = {
    "MORNING_NOTIFY": dt_time(7, 30),
    "DEBUG_NOTIFY": dt_time(14, 57),
    "AFTERNOON_NOTIFY": dt_time(17, 31)
}

# Default task style
TASK_STYLE = "ls"

# CSV file path
LOGIN_CSV_PATH = "storage/cache/login_info.csv"
VOICE_CACHE_PATH = "storage/downloads/cache/voice_reply_{}.mp3"

# Validation
if not TOKEN:
    raise ValueError("DISCORD_TOK is required.")
