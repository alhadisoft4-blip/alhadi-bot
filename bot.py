import os
import asyncio
import logging
from aiohttp import web
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError

# إعداد السجلات لمراقبة الأداء
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔒 الإعدادات الأساسية
TOKEN = os.environ.get("BOT_TOKEN", "8914679676:AAEeV07KSkz_w5y-qbESc0BTFxB9d5LOvhA")
CHANNEL_ID = '@AlhadiSoft'
CHANNEL_INVITE_LINK = 'https://t.me/+BIHVdkbZ_qY5OTM0'
PORT = int(os.environ.get("PORT", 8080))

# رابط السيرفر الخاص بك لمنع النوم (استبدله برابط Render الخاص بك إذا تغير)
APP_URL = "https://alhadi-bot.onrender.com"

user_urls = {}

COBALT_INSTANCES = [
    "https://api.cobalt.tools/api/json",
    "https://cobalt.fastest.workers.dev/api/json",
    "https://api.wukong.wtf/api/json",
    "https://cobalt-api.lcom.cloud/api/json"
]

# 🌐 1. خادم ويب حقيقي ومتوافق مع Render لحل مشكلة HTTP 502
async def handle_root(request):
    return web.Response(text="🚀 Alhadi Soft Engine is Running perfectly 24/7!", content_type="text/plain")

async def handle_health(request):
    return web.Response(text="OK", status=200)

async def start_webhook_server():
    app = web.Application()
    app.router.add_get('/', handle_root)
    app.router.add_get('/health', handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"✅ Web Server successfully bound to port {PORT}")

# 🔄 2. نظام التنشيط الذاتي الدائم لمنع خمول السيرفر (Self-Ping)
async def keep_alive_loop():
    await asyncio.sleep(30) # الانتظار حتى يستقر إقلاع السيرفر
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(APP_URL, timeout=10) as response:
                    if response.status == 200:
                        logger.info("⚡ Self-Ping successful. System kept alive.")
            except Exception as e:
                logger.warning(f"⚠️ Keep-alive ping missed: {e}")
            await asyncio.sleep(600) # فحص وتنشيط كل 10 دقائق منعاً للنوم

# 🤖 3. وظائف البوت الأساسية
async def is_subscribed(user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except TelegramError:
        return True 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_subscribed(user_id, context.bot):
        keyboard = [[InlineKeyboardButton("📢 اشترك في القناة هنا", url=CHANNEL_INVITE_LINK)]]
        await update.message.reply_text(
            "⚠️ عذراً! يجب عليك الاشتراك في قناة المؤسسة أولاً لتتمكن من استخدام البوت مجاناً.\n\n"
            "👇 اشترك عبر الرابط أدناه ثم أرسل /start مجدداً للتحقق والتشغيل:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    reply_keyboard = [
        [KeyboardButton("🟢 Start")],
        [KeyboardButton("💼 خدماتنا"), KeyboardButton("👥 فريق الدعم الهادي سوفت")]
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🚀 أهلاً بك في بوت التحميل غير القابل للحظر - مؤسسة الهادي سوفت!\n\n👇 أرسل رابط الفيديو مباشرة لبدء السحب الرقمي الآمن.",
        reply_markup=markup
    )

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    chat_id = update.message.chat_id
    
    if not await is_subscribed(user_id, context.bot):
        keyboard = [[InlineKeyboardButton("📢 اشترك في القناة هنا", url=CHANNEL_INVITE_LINK)]]
        await update.message.reply_text("⚠️ يرجى الاشتراك في القناة أولاً لتفعيل خدمات البوت:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if text == "🟢 Start":
        await update.message.reply_text("🔄 البوت نشط وجاهز تماماً، أرسل رابط الفيديو المُراد تحميله الآن.")
        return
    elif text == "💼 خدماتنا":
        await update.message.reply_text("🛠️ **خدمات مؤسسة الهادي سوفت:**\n\n👈 تطوير وترقية البوتات والأنظمة البرمجية بأحدث التقنيات السحابية العالمية.")
        return
    elif text == "👥 فريق الدعم الهادي سوفت":
        await update.message.reply_text("👋 للتواصل معنا مباشرة عبر الرابط التالي:\n👉 t.me/AlhadiSoft")
        return

    if text.startswith("http://") or text.startswith("https://"):
        user_urls[chat_id] = text
        buttons = [
            [InlineKeyboardButton("🎬 جودة عالية", callback_data="1080"), InlineKeyboardButton("🎬 جودة متوسطة", callback_data="720")],
            [InlineKeyboardButton("🎬 جودة عادية", callback_data="480"), InlineKeyboardButton("🎵 تحويله إلى صوت MP3", callback_data="audio")]
        ]
        await update.message.reply_text("📌 تم فحص الرابط بنجاح وتحضير نفق السحب السحابي!\n\n👇 اختر الجودة المطلوبة:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text("⚠️ يرجى إرسال رابط فيديو صحيح.")

async def try_download_from_instances(url, quality, is_audio):
    payload = {"url": url, "videoQuality": quality, "downloadMode": "audio" if is_audio else "video"}
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        for instance in COBALT_INSTANCES:
            try:
                async with session.post(instance, json=payload, headers=headers, timeout=12) as response:
                    if response.status == 200:
                        res_data = await response.json()
                        file_url = res_data.get("url")
                        if file_url:
                            return file_url
            except Exception:
                continue
    return None

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    choice = query.data
    url = user_urls.get(chat_id)
    
    if not url:
        await query.edit_message_text("❌ انتهت الجلسة، يرجى إرسال الرابط مجدداً.")
        return
        
    await query.edit_message_text("🔄 جاري كسر تشفير المنصة عبر الأنفاق الرقمية، يرجى الانتظار...")
    is_audio = (choice == "audio")
    quality = "720" if choice == "audio" else choice
    
    direct_file_url = await try_download_from_instances(url, quality, is_audio)
    
    if not direct_file_url:
        await query.edit_message_text("❌ جميع محاولات كسر الحظر فشلت، يرجى تجربة رابط آخر.")
        return

    await query.edit_message_text("🚀 تم اختراق الحظر بنجاح! جاري تحميل الملف سحابياً...")
    fn = f"{chat_id}_hadi." + ("mp3" if is_audio else "mp4")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(direct_file_url) as file_resp:
                if file_resp.status == 200:
                    with open(fn, "wb") as f:
                        async for chunk in file_resp.content.iter_chunked(1024 * 1024):
                            f.write(chunk)
                    
                    await query.edit_message_text("⚡ اكتملت المعالجة! جاري الرفع المباشر لـ تيليجرام...")
                    with open(fn, 'rb') as f:
                        if is_audio:
                            await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم تحويل الصوت بنجاح - الهادي سوفت")
                        else:
                            await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم سحب الفيديو بنجاح - الهادي سوفت")
                    
                    if os.path.exists(fn): os.remove(fn)
                    user_urls.pop(chat_id, None)
                else:
                    await query.edit_message_text("❌ فشل السيرفر في معالجة دفق البيانات.")
    except Exception:
        if os.path.exists(fn): os.remove(fn)
        await query.edit_message_text("❌ حدث خطأ أثناء الرفع، قد يكون حجم الملف كبيراً جداً.")

# ⚙️ 4. المحرك الأساسي لإدارة المهام المتزامنة معاً
async def main():
    # تشغيل خادم الويب المتوافق مع Render لحل خطأ الـ 502
    await start_webhook_server()
    
    # تشغيل حلقة التنشيط الذاتي لمنع خمول السيرفر ونومه
    asyncio.create_task(keep_alive_loop())
    
    # تهيئة وتشغيل البوت
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(CallbackQueryHandler(buttons_click if 'buttons_click' in globals() else button_click))
    
    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    
    logger.info("🚀 AlhadiSoft System Engine is fully armed and running 24/7!")
    
    # المحافظة على استمرار المهام الخلفية
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await app.updater.stop()
        await app.stop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        
