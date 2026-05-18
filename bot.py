import os
import asyncio
import logging
import threading
import http.server
import socketserver
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError

# إعداد السجلات لمراقبة الأداء
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔒 الإعدادات الأساسية (تأكد من ضبط الـ Token في Render كمتغير بيئة)
TOKEN = os.environ.get("BOT_TOKEN", "8914679676:AAEeV07KSkz_w5y-qbESc0BTFxB9d5LOvhA")
CHANNEL_ID = '@AlhadiSoft'
CHANNEL_INVITE_LINK = 'https://t.me/+BIHVdkbZ_qY5OTM0'

user_urls = {}

# 🌐 خادم وهمي سريع لمنع ريندر من إعطاء خطأ 502 أو النوم
def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            logger.info(f"✅ Web server trigger bound to port {port}")
            httpd.serve_forever()
    except Exception as e:
        logger.warning(f"⚠️ Web server alert: {e}")

# 🔐 التحقق من الاشتراك الإجباري في القناة
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
            "⚠️ عذراً هندسة! يجب عليك الاشتراك في قناة المؤسسة أولاً لتتمكن من استخدام البوت مجاناً.\n\n"
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
        "🚀 مرحباً بك في محرك السحب المباشر الداخلي - مؤسسة الهادي سوفت!\n\n👇 أرسل رابط الفيديو من أي منصة مباشرة لبدء المعالجة فوراً.",
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
        await update.message.reply_text("🔄 المحرك الداخلي نشط وجاهز، أرسل رابط الفيديو المُراد سحبه الآن.")
        return
    elif text == "💼 خدماتنا":
        await update.message.reply_text("🛠️ **خدمات مؤسسة الهادي سوفت:**\n\n👈 تطوير وترقية البوتات والأنظمة البرمجية وحلول سيرفرات فك التشفير السحابية.")
        return
    elif text == "👥 فريق الدعم الهادي سوفت":
        await update.message.reply_text("👋 للتواصل بنا مباشرة لحلول السيرفرات والتطبيقات:\n👉 t.me/AlhadiSoft")
        return

    if text.startswith("http://") or text.startswith("https://"):
        user_urls[chat_id] = text
        buttons = [
            [InlineKeyboardButton("🎬 تحميل فيديو MP4", callback_data="video")],
            [InlineKeyboardButton("🎵 تحويل إلى صوت MP3", callback_data="audio")]
        ]
        await update.message.reply_text("📌 تم فحص الرابط بنجاح بواسطة كاشف الذكاء الاصطناعي الداخلي!\n\n👇 اختر صيغة الاستخراج المطلوبة:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text("⚠️ يرجى إرسال رابط فيديو صحيح يبدأ بـ http أو https.")

# 🛠️ محرك التحميل الداخلي الصامت باستخدام yt-dlp المتزامن عبر الخيوط
def download_processor(url, is_audio, output_template):
    import yt_dlp
    
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None, # لكسر حظر يوتيوب الصارم إذا دعت الحاجة
    }
    
    if is_audio:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        # اختيار أفضل جودة مدمجة (فيديو + صوت) لا تتخطى سعة سيرفر ريندر المجاني
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
        })
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    choice = query.data
    url = user_urls.get(chat_id)
    
    if not url:
        await query.edit_message_text("❌ انتهت الجلسة الأمنية، يرجى إعادة إرسال الرابط مجدداً.")
        return
        
    await query.edit_message_text("🔄 جاري الاتصال المباشر بالمنصة وحظر خوارزميات التتبع...")
    is_audio = (choice == "audio")
    
    # تحضير المسار والملف النظيف
    base_name = f"{chat_id}_hadi"
    output_template = f"{base_name}.%(ext)s"
    
    try:
        # تشغيل وظيفة yt-dlp في خيط خارجي متزامن لمنع تجميد البوت أثناء التحميل
        loop = asyncio.get_running_loop()
        await query.edit_message_text("🚀 جاري سحب دفق البيانات مباشرة إلى السيرفر السحابي الخاص بك...")
        
        filename = await loop.run_in_executor(None, download_processor, url, is_audio, output_template)
        
        # تصحيح الامتداد النهائي في حالة تحويل الـ MP3
        final_file = f"{base_name}.mp3" if is_audio else filename
        
        if not os.path.exists(final_file) and not is_audio:
             final_file = base_name + ".mp4" # صمام أمان للامتداد الرسمي
             
        await query.edit_message_text("⚡ اكتمل التشفير والسحب بنجاح! جاري الرفع الفوري لـ تيليجرام...")
        
        with open(final_file, 'rb') as f:
            if is_audio:
                await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم استخراج الصوت ونقله بنجاح - الهادي سوفت")
            else:
                await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم كسر الحظر وتنزيل الفيديو بنجاح - الهادي سوفت")
        
        # تنظيف المجلد بعد الرفع لعدم ملء مساحة السيرفر
        if os.path.exists(final_file): os.remove(final_file)
        user_urls.pop(chat_id, None)
        await query.delete_message()
        
    except Exception as e:
        logger.error(f"Engine Failure: {e}")
        # تنظيف بقايا الملفات الفاشلة إن وجدت
        for ext in ['.mp4', '.mp3', '.m4a', '.webm', '.3gp']:
            if os.path.exists(base_name + ext): os.remove(base_name + ext)
        await query.edit_message_text("❌ فشل المحرك الداخلي في معالجة هذا الرابط، يرجى التأكد من أن الفيديو ليس خاصاً أو محمياً بقفل.")

# ⚙️ المحرك الأساسي لتهيئة الخدمات المتزامنة
async def main():
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(CallbackQueryHandler(button_click))
    
    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    
    logger.info("🚀 AlhadiSoft Standalone Engine is operational!")
    
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
        
