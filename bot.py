import os
import asyncio
import logging
import threading
import http.server
import socketserver
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# إعدادات الـ Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "8914679676:AAEeV07KSkz_w5y-qbESc0BTFxB9d5LOvhA")

# قاموس لحفظ روابط المستخدمين وحالة القفل لمنع المعالجة المتزامنة لنفس المستخدم
user_urls = {}
user_locks = {}

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            logger.info(f"✅ Web server bound to port {port}")
            httpd.serve_forever()
    except Exception as e:
        logger.warning(f"⚠️ Web server notice: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [[KeyboardButton("🟢 Start")]]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🚀 مرحباً بك في بوت سحب الوسائط الاحترافي المطور!\n\n👇 أرسل رابط الفيديو المُراد معالجته الآن.",
        reply_markup=markup
    )

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.message.chat_id
    
    if text == "🟢 Start":
        await update.message.reply_text("🔄 النظام جاهز ومستقر، أرسل الرابط مباشرة.")
        return

    if text.startswith("http://") or text.startswith("https://"):
        # ⚠️ محاكاة نظام البوت المستهدف: التحقق مما إذا كان المستخدم يمتلك عملية قيد المعالجة حالياً
        if user_locks.get(chat_id, False):
            await update.message.reply_text(
                "⚠️ عذراً، في الوقت الحالي يتم معالجة طلبك السابق بواسطة نظامنا.\n"
                "انتظر حتى نهاية التنزيل أو حاول مرة أخرى لاحقاً خلال دقيقة."
            )
            return

        user_urls[chat_id] = text
        
        # جلب معلومات الفيديو وحجمه بشكل سريع لتوليد الأزرار الديناميكية
        await update.message.reply_text("🔄 جاري فحص الرابط واستخراج الأحجام...")
        
        loop = asyncio.get_running_loop()
        try:
            info = await loop.run_in_executor(None, fetch_video_info, text)
            filesize_str = info.get('size_str', 'غير محدد')
            title = info.get('title', 'فيديو')
            
            buttons = [
                [InlineKeyboardButton(f"📥 تحميل {title[:20]} ~ {filesize_str}", callback_data="video")],
                [InlineKeyboardButton("🎵 قم بتنزيل الصوت (MP3)", callback_data="audio")],
                [InlineKeyboardButton("📱 وضع متوافق مع Apple iOS", callback_data="ios")]
            ]
            await update.message.reply_text(
                f"📊 **الاستخدام اليومي:**\nحركة المرور: متاح بالكامل\n\n**العنوان:** {title}\n\n👇 اختر صيغة التحميل المطلوبة:", 
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            await update.message.reply_text(f"❌ فشل السيرفر في قراءة بيانات الرابط الحالية.\nالوصف: {str(e)[:50]}")
    else:
        await update.message.reply_text("⚠️ يرجى إرسال رابط صحيح يبدأ بـ http أو https.")

# دالة سريعة لجلب بيانات المقطع وحجمه التقديمي
def fetch_video_info(url):
    import yt_dlp
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        # محاولة حساب الحجم التقديري للملف
        filesize = info.get('filesize') or info.get('filesize_approx')
        if filesize:
            size_mb = filesize / (1024 * 1024)
            size_str = f"{size_mb:.2f} MB"
        else:
            size_str = "تحميل مباشر"
        return {'title': info.get('title', 'Video'), 'size_str': size_str}

# محرك السحب الهجين والآمن ضد الحظر
def download_processor(url, mode, output_template):
    import yt_dlp
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        },
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
    }
    
    if mode == "audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    elif mode == "ios":
        # ترميز متوافق ومضمون لأجهزة أبل القديمة والحديثة
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })
    else:
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
        await query.edit_message_text("❌ انتهت الجلسة الأمنية، يرجى إعادة إرسال الرابط.")
        return
        
    # تفعيل قفل المستخدم لحمايته من إرسال روابط أخرى أثناء التحميل
    user_locks[chat_id] = True
    await query.edit_message_text("🔄 جاري سحب وتجهيز ملف الوسائط عبر النفق السحابي الخاص...")
    
    base_name = f"{chat_id}_hadi"
    output_template = f"{base_name}.%(ext)s"
    
    try:
        loop = asyncio.get_running_loop()
        filename = await loop.run_in_executor(None, download_processor, url, choice, output_template)
        
        final_file = f"{base_name}.mp3" if choice == "audio" else filename
        if not os.path.exists(final_file) and choice != "audio":
             final_file = base_name + ".mp4"
             
        await query.edit_message_text("⚡ اكتمل التنزيل بنجاح! جاري الرفع الفوري للمنصة...")
        
        with open(final_file, 'rb') as f:
            if choice == "audio":
                await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم استخراج الصوت بنجاح.")
            else:
                await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم تحميل المقطع بنجاح.")
        
        if os.path.exists(final_file): os.remove(final_file)
        user_urls.pop(chat_id, None)
        await query.delete_message()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        for ext in ['.mp4', '.mp3', '.m4a', '.webm']:
            if os.path.exists(base_name + ext): os.remove(base_name + ext)
        await query.edit_message_text(f"❌ عذراً! واجه السيرفر عائقاً أثناء المعالجة النفقية.\nالوصف: {str(e)[:60]}")
    finally:
        # إزالة القفل بعد انتهاء العملية تماماً سواء نجحت أو فشلت
        user_locks[chat_id] = False

# 🛠️ حل مشكلة الـ Loop عبر معالج إقلاع السيرفر الحديث والمستقر
async def main():
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(CallbackQueryHandler(button_click))
    
    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    
    logger.info("🚀 System initialized safely on all cloud platforms!")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await app.updater.stop()
        await app.stop()

if __name__ == '__main__':
    # حائط الصد النهائي لمنع خطأ RuntimeError في السيرفرات السحابية
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        nested_task = loop.create_task(main())
    else:
        loop.run_until_complete(main())
