import os
import logging
import requests
import re
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

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

def start(update, context):
    keyboard = [
        [InlineKeyboardButton("📱 دریافت شماره تونس", callback_data="get_number")],
        [InlineKeyboardButton("💰 بررسی موجودی", callback_data="check_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "🤖 به ربات دریافت شماره تونس خوش آمدید!",
        reply_markup=reply_markup
    )

def handle_callback(update, context):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    
    if query.data == "get_number":
        get_number(query, user_id)
    elif query.data == "check_balance":
        check_balance(query)
    elif query.data == "get_code":
        get_sms_code(query, user_id)
    elif query.data == "back":
        start_callback(update, context)

def start_callback(update, context):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("📱 دریافت شماره تونس", callback_data="get_number")],
        [InlineKeyboardButton("💰 بررسی موجودی", callback_data="check_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "🤖 به ربات دریافت شماره تونس خوش آمدید!",
        reply_markup=reply_markup
    )

def get_number(query, user_id):
    try:
        query.edit_message_text("📞 درحال دریافت شماره...")
        
        url = "https://grizzlysms.com/api/v1/order"
        params = {"key": API_KEY, "service": "telegram", "country": "tn"}
        
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        logger.info(f"API Response: {data}")
        
        if data.get("status") == "success":
            phone_number = data["data"]["number"]
            order_id = data["data"]["order_id"]
            
            user_sessions[user_id] = {
                "order_id": order_id,
                "phone_number": phone_number
            }
            
            keyboard = [
                [InlineKeyboardButton("🔄 دریافت کد تأیید", callback_data="get_code")],
                [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"✅ **شماره دریافت شد!**\n\n"
                f"📱 **شماره:** `{phone_number}`\n"
                f"🆔 **Order ID:** `{order_id}`\n\n"
                f"📝 این شماره را در تلگرام وارد کنید و سپس روی 'دریافت کد تأیید' کلیک کنید.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            error_msg = data.get('message', 'خطای ناشناخته')
            query.edit_message_text(f"❌ خطا در دریافت شماره: {error_msg}")
            
    except Exception as e:
        logger.error(f"Error in get_number: {e}")
        query.edit_message_text("❌ خطا در ارتباط با سرور")

def get_sms_code(query, user_id):
    try:
        if user_id not in user_sessions:
            query.edit_message_text("❌ session شما منقضی شده است. لطفاً دوباره شروع کنید.")
            return
            
        order_id = user_sessions[user_id]["order_id"]
        phone_number = user_sessions[user_id]["phone_number"]
        
        query.edit_message_text("⏳ در حال دریافت کد تأیید... لطفاً منتظر بمانید.")
        
        url = "https://grizzlysms.com/api/v1/sms"
        params = {"key": API_KEY, "order_id": order_id}
        
        for i in range(12):
            try:
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
                    
                    keyboard = [
                        [InlineKeyboardButton("📱 دریافت شماره جدید", callback_data="get_number")],
                        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    query.edit_message_text(
                        f"🎉 **کد تأیید دریافت شد!**\n\n"
                        f"📱 **شماره:** `{phone_number}`\n"
                        f"🔢 **کد تأیید:** `{final_code}`\n\n"
                        f"✅ این کد را در تلگرام وارد کنید.",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                    return
                
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error checking SMS: {e}")
                time.sleep(10)
        
        query.edit_message_text("❌ کد تأیید دریافت نشد. لطفاً دوباره تلاش کنید.")
        
    except Exception as e:
        logger.error(f"Error in get_sms_code: {e}")
        query.edit_message_text("❌ خطا در دریافت کد")

def check_balance(query):
    try:
        query.edit_message_text("💰 در حال بررسی موجودی...")
        
        url = "https://grizzlysms.com/api/v1/balance"
        params = {"key": API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "success":
            balance = data["data"].get("balance", 0)
            currency = data["data"].get("currency", "USD")
            
            keyboard = [
                [InlineKeyboardButton("📱 دریافت شماره", callback_data="get_number")],
                [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"💳 **موجودی حساب:**\n\n"
                f"💰 **مبلغ:** {balance} {currency}\n\n"
                f"برای دریافت شماره جدید از دکمه زیر استفاده کنید:",
                reply_markup=reply_markup
            )
        else:
            query.edit_message_text("❌ خطا در بررسی موجودی")
            
    except Exception as e:
        logger.error(f"Error in check_balance: {e}")
        query.edit_message_text("❌ خطا در ارتباط با سرور")

def main():
    logger.info("🚀 Starting Telegram Bot...")
    
    try:
        # ساخت آپدیتور بدون use_context
        updater = Updater(BOT_TOKEN)
        dispatcher = updater.dispatcher
        
        # اضافه کردن هندلرها
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CallbackQueryHandler(handle_callback))
        
        logger.info("✅ Bot is running and polling...")
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    main()
