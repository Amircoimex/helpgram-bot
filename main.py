import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import requests
import re

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# چک کردن متغیرهای محیطی
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
API_KEY = os.environ.get('GRIZZLYSMS_API_KEY')

print("=" * 50)
print("🔍 بررسی متغیرهای محیطی:")
print(f"BOT_TOKEN: {'✅ موجود' if BOT_TOKEN else '❌ Missing'}")
print(f"API_KEY: {'✅ موجود' if API_KEY else '❌ Missing'}")
print("=" * 50)

if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN not set in environment variables!")
    exit(1)

if not API_KEY:
    logger.error("❌ GRIZZLYSMS_API_KEY not set in environment variables!")
    exit(1)

# دیکشنری برای ذخیره وضعیت کاربران
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"سلام {user.first_name}! 👋\n"
        "🤖 به ربات دریافت شماره تونس خوش آمدید!\n\n"
        "برای شروع از دکمه‌های زیر استفاده کنید:"
    )
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی"""
    keyboard = [
        [InlineKeyboardButton("📱 دریافت شماره تونس", callback_data="get_number")],
        [InlineKeyboardButton("💰 بررسی موجودی", callback_data="check_balance")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "منوی اصلی:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "منوی اصلی:",
            reply_markup=reply_markup
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    elif query.data == "get_code":
        await get_sms_code(query, user_id)
    elif query.data == "cancel":
        if user_id in user_sessions:
            del user_sessions[user_id]
        await query.edit_message_text("❌ عملیات لغو شد.")
        await show_main_menu(update, context)
    elif query.data == "main_menu":
        await show_main_menu(update, context)

async def get_tunisian_number(query, user_id):
    """دریافت شماره تونس"""
    try:
        await query.edit_message_text("📞 در حال دریافت شماره تونس...")
        
        url = "https://grizzlysms.com/api/v1/order"
        params = {
            "key": API_KEY,
            "service": "telegram", 
            "country": "tn"
        }
        
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        logger.info(f"API Response: {data}")
        
        if data.get("status") == "success":
            phone_number = data["data"]["number"]
            order_id = data["data"]["order_id"]
            
            # ذخیره اطلاعات کاربر
            user_sessions[user_id] = {
                "order_id": order_id,
                "phone_number": phone_number,
                "status": "waiting_for_code"
            }
            
            keyboard = [
                [InlineKeyboardButton("🔄 دریافت کد تأیید", callback_data="get_code")],
                [InlineKeyboardButton("❌ لغو", callback_data="cancel")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
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
            error_msg = data.get('message', 'خطای ناشناخته')
            await query.edit_message_text(
                f"❌ خطا در دریافت شماره:\n{error_msg}\n\n"
                "لطفاً دوباره تلاش کنید."
            )
            
    except Exception as e:
        logger.error(f"Error getting number: {e}")
        await query.edit_message_text(
            "❌ خطا در ارتباط با سرور\n\n"
            "لطفاً چند دقیقه دیگر تلاش کنید."
        )

async def get_sms_code(query, user_id):
    """دریافت کد SMS"""
    try:
        if user_id not in user_sessions:
            await query.edit_message_text("❌ session شما منقضی شده است. لطفا دوباره شروع کنید.")
            return
            
        order_id = user_sessions[user_id]["order_id"]
        phone_number = user_sessions[user_id]["phone_number"]
        
        await query.edit_message_text("⏳ در حال دریافت کد تأیید... لطفاً منتظر بمانید.")
        
        url = "https://grizzlysms.com/api/v1/sms"
        params = {"key": API_KEY, "order_id": order_id}
        
        # چک کردن کد برای 3 دقیقه
        for i in range(18):
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
                    
                    # حذف session کاربر
                    del user_sessions[user_id]
                    
                    keyboard = [
                        [InlineKeyboardButton("📱 دریافت شماره جدید", callback_data="get_number")],
                        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
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
                
                # اگر کد نیومده، پیام پیشرفت بدیم
                if i % 3 == 0:  # هر 30 ثانیه
                    await query.edit_message_text(
                        f"⏳ در حال دریافت کد تأیید... ({i+1}/18)\n"
                        f"لطفاً منتظر بمانید."
                    )
                
            except Exception as e:
                logger.error(f"Error checking SMS: {e}")
            
        # اگر کد دریافت نشد
        await query.edit_message_text(
            "❌ کد تأیید دریافت نشد.\n\n"
            "ممکن است:\n"
            "• شماره را درست وارد نکرده‌اید\n"
            "• زمان دریافت کد گذشته است\n"
            "• مشکل از سرویس SMS است\n\n"
            "لطفاً دوباره تلاش کنید."
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
                [InlineKeyboardButton("📱 دریافت شماره", callback_data="get_number")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
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

1. **📱 دریافت شماره**: یک شماره تونس برای ثبت‌نام در تلگرام دریافت کنید
2. **📝 ثبت در تلگرام**: شماره را در اپلیکیشن تلگرام وارد کنید
3. **🔄 دریافت کد**: روی "دریافت کد تأیید" کلیک کنید
4. **✅ تکمیل ثبت‌نام**: کد را در تلگرام وارد کنید

⚠️ **نکات مهم:**
• پس از دریافت شماره، حداکثر 3 دقیقه فرصت دارید
• شماره‌ها فقط برای ثبت‌نام در تلگرام قابل استفاده هستند
• در صورت مشکل، دوباره امتحان کنید
"""
    
    keyboard = [
        [InlineKeyboardButton("📱 دریافت شماره", callback_data="get_number")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(help_text, reply_markup=reply_markup)

def main():
    """اجرای اصلی بات"""
    logger.info("🚀 شروع راه‌اندازی بات...")
    
    try:
        # ساخت اپلیکیشن
        application = Application.builder().token(BOT_TOKEN).build()
        
        # اضافه کردن handler ها
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        # اجرای بات
        logger.info("✅ بات در حال اجرا...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ خطا در اجرای بات: {e}")
        raise

if __name__ == "__main__":
    main()