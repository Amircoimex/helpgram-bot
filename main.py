import os
import logging
import requests
import re
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 دریافت شماره تونس", callback_data="get_number")],
        [InlineKeyboardButton("💰 بررسی موجودی", callback_data="check_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 به ربات دریافت شماره تونس خوش آمدید!",
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "get_number":
        await get_number(query, user_id)
    elif query.data == "check_balance":
        await check_balance(query)
    elif query.data == "get_code":
        await get_sms_code(query, user_id)

async def get_number(query, user_id):
    try:
        await query.edit_message_text("📞 درحال دریافت شماره...")
        
        url = "https://grizzlysms.com/api/v1/order"
        params = {"key": API_KEY, "service": "telegram", "country": "tn"}
        
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if data.get("status") == "success":
            phone_number = data["data"]["number"]
            order_id = data["data"]["order_id"]
            
            user_sessions[user_id] = {"order_id": order_id, "phone_number": phone_number}
            
            keyboard = [
                [InlineKeyboardButton("🔄 دریافت کد", callback_data="get_code")],
                [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ شماره دریافت شد:\n`{phone_number}`\n\nاین شماره رو در تلگرام وارد کن.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ خطا در دریافت شماره")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        await query.edit_message_text("❌ خطا در ارتباط")

async def get_sms_code(query, user_id):
    try:
        if user_id not in user_sessions:
            await query.edit_message_text("❌ session منقضی شده")
            return
            
        order_id = user_sessions[user_id]["order_id"]
        phone_number = user_sessions[user_id]["phone_number"]
        
        await query.edit_message_text("⏳ درحال دریافت کد...")
        
        url = "https://grizzlysms.com/api/v1/sms"
        params = {"key": API_KEY, "order_id": order_id}
        
        for i in range(12):
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get("status") == "success" and data["data"].get("sms"):
                sms_code = data["data"]["sms"]
                code_match = re.search(r'\b\d{4,6}\b', sms_code)
                
                if code_match:
                    final_code = code_match.group()
                else:
                    final_code = sms_code
                
                del user_sessions[user_id]
                await query.edit_message_text(f"✅ کد دریافت شد:\n`{final_code}`", parse_mode="Markdown")
                return
            
            import asyncio
            await asyncio.sleep(10)
        
        await query.edit_message_text("❌ کد دریافت نشد")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await query.edit_message_text("❌ خطا در دریافت کد")

async def check_balance(query):
    try:
        await query.edit_message_text("💰 درحال بررسی موجودی...")
        
        url = "https://grizzlysms.com/api/v1/balance"
        params = {"key": API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "success":
            balance = data["data"].get("balance", 0)
            currency = data["data"].get("currency", "USD")
            await query.edit_message_text(f"💰 موجودی: {balance} {currency}")
        else:
            await query.edit_message_text("❌ خطا در بررسی موجودی")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        await query.edit_message_text("❌ خطا در ارتباط")

def main():
    logger.info("🚀 Starting Bot...")
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not set!")
        return
    
    try:
        # استفاده از Application به جای Updater
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        logger.info("✅ Bot is running...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
