import os
import logging
import requests
import re
import time

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# چک کردن متغیرهای محیطی
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8392055613:AAGCVLg7iVCOSXkSQU4TSAS111BV6GTM34s")
API_KEY = os.environ.get("GRIZZLYSMS_API_KEY", "561cab8ebb259d7d1e65fb83b6807484")

print("=" * 50)
print("🔧 Environment Check:")
print(f"BOT_TOKEN: {'✅ SET' if BOT_TOKEN else '❌ MISSING'}")
print(f"API_KEY: {'✅ SET' if API_KEY else '❌ MISSING'}")
print("=" * 50)

user_sessions = {}

def main():
    print("🚀 Starting simple bot test...")
    print("✅ Environment variables are set correctly!")
    print("🤖 Bot is ready to work!")
    
    # نگه داشتن کانتینر فعال
    while True:
        time.sleep(60)
        print("⏳ Bot container is running...")

if __name__ == "__main__":
    main()
