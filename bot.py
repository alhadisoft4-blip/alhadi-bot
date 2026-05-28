import os
import asyncio
import logging
import threading
import http.server
import socketserver
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# إعدادات الـ Logging لمراقبة السيرفر
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "8914679676:AAEeV07KSkz_w5y-qbESc0BTFxB9d5LOvhA")

# قواميس إدارة الجلسات والتحكم في طابور المستخدمين
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
        "🚀 مرحباً بك في بوت سحب الوسائط الاحترافي (المطور لكسر الحظر)!\n\n👇 أرسل رابط الفيديو المُراد معالجته الآن.",
        reply_markup=markup
    )

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.message.chat_id
    
    if text == "🟢 Start":
        await update.message.reply_text("🔄 النظام جاهز ومستقر، أرسل الرابط مباشرة هندسة.")
        return

    if text.startswith("http://") or text.startswith("https://"):
        # نظام طابور الحماية: منع معالجة طلبين في نفس الوقت لنفس المستخدم
        if user_locks.get(chat_id, False):
            await update.message.reply_text(
                "⚠️ عذراً، في الوقت الحالي يتم معالجة طلبك السابق بواسطة نظامنا.\n"
                "انتظر حتى نهاية التنزيل أو حاول مرة أخرى لاحقاً."
            )
            return

        user_urls[chat_id] = text
        await update.message.reply_text("🔄 جاري فحص الرابط عبر مشغل iOS السحابي واستخراج الأحجام...")
        
        loop = asyncio.get_running_loop()
        try:
            # استدعاء دالة الفحص المحدثة
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
            await update.message.reply_text(f"❌ فشل السيرفر في قراءة بيانات الرابط الحالية.\nالوصف: {str(e)[:100]}")
    else:
        await update.message.reply_text("⚠️ يرجى إرسال رابط صحيح يبدأ بـ http أو https.")

# 🛠️ [تحديث] دالة الفحص السريع عبر محاكاة مشغل آبل للـ Shorts لتفادي جدار حماية يوتيوب
def fetch_video_info(url):
    import yt_dlp
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        # كسر الحظر: إجبار يوتيوب على التعامل مع السيرفر كأنه هاتف آيفون يقرأ مقطع Shorts مجاني
        'extractor_args': {
            'youtube': {
                'player_client': ['ios'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1',
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        filesize = info.get('filesize') or info.get('filesize_approx')
        if filesize:
            size_mb = filesize / (1024 * 1024)
            size_str = f"{size_mb:.2f} MB"
        else:
            size_str = "تحميل مباشر"
        return {'title': info.get('title', 'Video'), 'size_str': size_str}

# 🛠️ [تحديث] محرك التنزيل والمعالجة الرئيسي المقاوم للحظر
def download_processor(url, mode, output_template):
    import yt_dlp
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        # كسر الحظر: فرض مشغل iOS حصراً لتخطي خطأ (Sign in to confirm)
        'extractor_args': {
            'youtube': {
                'player_client': ['ios'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1',
        }
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
        
    # تفعيل قفل المستخدم
    user_locks[chat_id] = True
    await query.edit_message_text("🔄 جاري سحب وتجهيز ملف الوسائط عبر نفق التمويه المخفي...")
    
    base_name = f"{chat_id}_hadi"
    output_template = f"{base_name}.%(ext)s"
    
    try:
        loop = asyncio.get_running_loop()
        filename = await loop.run_in_executor(None, download_processor, url, choice, output_template)
        
        final_file = f"{base_name}.mp3" if choice == "audio" else filename
        if not os.path.exists(final_file) and choice != "audio":
             final_file = base_name + ".mp4"
             
        await query.edit_message_text("⚡ اكتمل التنزيل بنجاح من يوتيوب! جاري النقل السريع إلى تيليجرام...")
        
        with open(final_file, 'rb') as f:
            if choice == "audio":
                await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم استخراج الصوت بنجاح - الهادي سوفت")
            else:
                await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم كسر الحظر وتنزيل الفيديو بنجاح - الهادي سوفت")
        
        if os.path.exists(final_file): os.remove(final_file)
        user_urls.pop(chat_id, None)
        await query.delete_message()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        for ext in ['.mp4', '.mp3', '.m4a', '.webm']:
            if os.path.exists(base_name + ext): os.remove(base_name + ext)
        await query.edit_message_text(f"❌ عذراً! واجه مشغل iOS عائقاً أثناء سحب هذا الرابط.\nالوصف: {str(e)[:80]}")
    finally:
        # فك قفل المستخدم ليدخل في الطلب التالي
        user_locks[chat_id] = False

async def main():
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(CallbackQueryHandler(button_click))
    
    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    
    logger.info("🚀 Safely launched with Anti-Block iOS Engine!")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await app.updater.stop()
        await app.stop()

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        nested_task = loop.create_task(main())
    else:
        loop.run_until_complete(main())
            
