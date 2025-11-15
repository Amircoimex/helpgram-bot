import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
import re

# تنظیمات
API_KEY = os.environ.get("GRIZZLYSMS_API_KEY")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# دیکشنری برای ذخیره وضعیت کاربران
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    keyboard = [
        [InlineKeyboardButton("📱 دریافت شماره تونس", callback_data="get_number")],
        [InlineKeyboardButton("💰 بررسی موجودی", callback_data="check_balance")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **به ربات دریافت شماره تونس خوش آمدید!**\n\n"
        "برای دریافت شماره تونس برای ثبت‌نام در تلگرام از دکمه زیر استفاده کنید:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "get_number":
        await get_tunisian_number(query, user_id)
    elif query.data == "check_balance":
        await check_balance(query)
    elif query.data == "help":
        await help_command(query)

async def get_tunisian_number(query, user_id):
    """دریافت شماره تونس"""
    try:
        await query.edit_message_text("📞 در حال دریافت شماره تونس...")
        
        # درخواست از API
        url = "https://grizzlysms.com/api/v1/order"
        params = {
            "key": API_KEY,
            "service": "telegram", 
            "country": "tn"
        }
        
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if data.get("status") == "success":
            phone_number = data["data"]["number"]
            order_id = data["data"]["order_id"]
            
            # ذخیره اطلاعات کاربر
            user_sessions[user_id] = {
                "order_id": order_id,
                "phone_number": phone_number,  # اینجا ویرایش شد
                "status": "waiting_for_code"
            }
            
            keyboard = [
                [InlineKeyboardButton("🔄 دریافت کد تأیید", callback_data="get_code")],
                [InlineKeyboardButton("❌ لغو", callback_data="cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ **شماره دریافت شد!**\n\n"
                f"📱 **شماره:** `{phone_number}`\n"
                f"🆔 **Order ID:** `{order_id}`\n\n"
                f"📝 این شماره را در تلگرام وارد کنید و سپس روی 'دریافت کد تأیید' کلیک کنید.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"❌ خطا در دریافت شماره:\n{data.get('message', 'خطای ناشناخته')}"
            )
            
    except Exception as e:
        logger.error(f"Error getting number: {e}")
        await query.edit_message_text("❌ خطا در ارتباط با سرور")

async def get_sms_code(query, user_id):
    """دریافت کد SMS"""
    try:
        if user_id not in user_sessions:
            await query.edit_message_text("❌ session شما منقضی شده است. لطفا دوباره شروع کنید.")
            return
            
        order_id = user_sessions[user_id]["order_id"]
        phone_number = user_sessions[user_id]["phone_number"]
        
        await query.edit_message_text("⏳ در حال دریافت کد تأیید...")
        
        url = "https://grizzlysms.com/api/v1/sms"
        params = {"key": API_KEY, "order_id": order_id}
        
        # چک کردن کد برای 3 دقیقه
        for i in range(18):
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get("status") == "success" and data["data"].get("sms"):
                sms_code = data["data"]["sms"]
                code_match = re.search(r'\b\d{4,6}\b', sms_code)
                
                if code_match:
                    final_code = code_match.group()
                else:
                    final_code = sms_code
                
                # حذف session کاربر
                del user_sessions[user_id]
                
                keyboard = [
                    [InlineKeyboardButton("📱 دریافت شماره جدید", callback_data="get_number")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🎉 **کد تأیید دریافت شد!**\n\n"
                    f"📱 **شماره:** `{phone_number}`\n"
                    f"🔢 **کد تأیید:** `{final_code}`\n\n"
                    f"✅ این کد را در تلگرام وارد کنید.",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return
            
            await asyncio.sleep(10)
        
        # اگر کد دریافت نشد
        await query.edit_message_text(
            "❌ کد تأیید دریافت نشد. ممکن است:\n"
            "• شماره را درست وارد نکرده‌اید\n"
            "• زمان دریافت کد گذشته است\n"
            "• مشکل از سرویس SMS است"
        )
        
    except Exception as e:
        logger.error(f"Error getting SMS: {e}")
        await query.edit_message_text("❌ خطا در دریافت کد")

async def check_balance(query):
    """بررسی موجودی"""
    try:
        await query.edit_message_text("💰 در حال بررسی موجودی...")
        
        url = "https://grizzlysms.com/api/v1/balance"
        params = {"key": API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "success":
            balance = data["data"].get("balance", 0)
            currency = data["data"].get("currency", "USD")
            
            keyboard = [
                [InlineKeyboardButton("📱 دریافت شماره", callback_data="get_number")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"💳 **موجودی حساب:**\n\n"
                f"💰 **مبلغ:** {balance} {currency}\n\n"
                f"برای دریافت شماره جدید از دکمه زیر استفاده کنید:",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("❌ خطا در بررسی موجودی")
            
    except Exception as e:
        logger.error(f"Error checking balance: {e}")
        await query.edit_message_text("❌ خطا در ارتباط با سرور")

async def help_command(query):
    """دستور راهنما"""
    help_text = """
📖 **راهنمای ربات:**

1. **دریافت شماره**: یک شماره تونس برای ثبت‌نام در تلگرام دریافت کنید
2. **ثبت در تلگرام**: شماره را در اپلیکیشن تلگرام وارد کنید
3. **دریافت کد**: روی "دریافت کد تأیید" کلیک کنید
4. **تکمیل ثبت‌نام**: کد را در تلگرام وارد کنید

⚠️ **نکات مهم:**
• پس از دریافت شماره، حداکثر 3 دقیقه فرصت دارید
• شماره‌ها فقط برای ثبت‌نام در تلگرام قابل استفاده هستند
• در صورت مشکل، دوباره امتحان کنید
"""
    
    keyboard = [
        [InlineKeyboardButton("📱 دریافت شماره", callback_data="get_number")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(help_text, reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیه callback ها"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if query.data == "get_number":
        await get_tunisian_number(query, user_id)
    elif query.data == "get_code":
        await get_sms_code(query, user_id)
    elif query.data == "check_balance":
        await check_balance(query)
    elif query.data == "help":
        await help_command(query)
    elif query.data == "cancel":
        if user_id in user_sessions:
            del user_sessions[user_id]
        await query.edit_message_text("❌ عملیات لغو شد.")

def main():
    """اجرای اصلی بات"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    if not API_KEY:
        logger.error("GRIZZLYSMS_API_KEY not set!")
        return
    
    # ساخت اپلیکیشن
    application = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن handler ها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # اجرای بات
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
