# config.py — TachZone Hosting Bot

import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8734287278:AAE3gUtc5-sF1MD4FnVKlqnXWamtmfXkJOY")
ADMIN_ID  = int(os.environ.get("ADMIN_ID", "7318114944"))
MAX_BOTS  = int(os.environ.get("MAX_BOTS", "5"))

# Railway Volume → /data এ persistent storage
_DATA_DIR = "/data"
os.makedirs(_DATA_DIR, exist_ok=True)

DB_FILE  = os.path.join(_DATA_DIR, "tachzone.db")
BASE_DIR = os.path.join(_DATA_DIR, "users")
os.makedirs(BASE_DIR, exist_ok=True)