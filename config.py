import os

BOT_TOKEN = "8734287278:AAE3gUtc5-sF1MD4FnVKlqnXWamtmfXkJOY"
ADMIN_ID = 7318114944
MAX_BOTS = 5

BASE_DIR = "users"
DB_FILE = "tachzone.db"
DB_PATH = os.path.join(BASE_DIR, DB_FILE)

os.makedirs(BASE_DIR, exist_ok=True)
print(f"✅ Config loaded | DB: {DB_PATH}")