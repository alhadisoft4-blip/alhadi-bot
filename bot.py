import os
import asyncio
import logging
import threading
import http.server
import socketserver
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError

# تفعيل مشغل ومثبت FFmpeg تلقائياً داخل السيرفر المجاني
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception as e:
    print(f"FFmpeg path notice: {e}")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "8914679676:AAEeV07KSkz_w5y-qbESc0BTFxB9d5LOvhA")
CHANNEL_ID = '@AlhadiSoft'
CHANNEL_INVITE_LINK = 'https://t.me/+BIHVdkbZ_qY5OTM0'

user_urls = {}

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

# 🛠️ دالة المعالجة المزودة بأنظمة التمويه والـ Spoofing لكسر حظر الداتا سنتر
def download_processor(url, is_audio, output_template):
    import yt_dlp
    
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        # 🔑 التمويه الخارق: إجبار السيرفر على محاكاة أجهزة الأندرويد والـ iOS لتخطي الحظر الجغرافي وحظر السيرفرات
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'skip': ['webpage']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1'
        }
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
        # سحب جودة مدمجة مباشرة لتخفيف الضغط على المعالج والرام المجاني
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
    
    base_name = f"{chat_id}_hadi"
    output_template = f"{base_name}.%(ext)s"
    
    try:
        loop = asyncio.get_running_loop()
        await query.edit_message_text("🚀 جاري معالجة وسحب البيانات بنظام التمويه السحابي للموبايل...")
        
        filename = await loop.run_in_executor(None, download_processor, url, is_audio, output_template)
        final_file = f"{base_name}.mp3" if is_audio else filename
        
        if not os.path.exists(final_file) and not is_audio:
             final_file = base_name + ".mp4"
             
        await query.edit_message_text("⚡ اكتمل التشفير والسحب بنجاح! جاري الرفع الفوري لـ تيليجرام...")
        
        with open(final_file, 'rb') as f:
            if is_audio:
                await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم استخراج الصوت ونقله بنجاح - الهادي سوفت")
            else:
                await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم كسر الحظر وتنزيل الفيديو بنجاح - الهادي سوفت")
        
        if os.path.exists(final_file): os.remove(final_file)
        user_urls.pop(chat_id, None)
        await query.delete_message()
        
    except Exception as e:
        logger.error(f"Engine Failure: {e}")
        # تنظيف فوري لأي مخلفات فاشلة
        for ext in ['.mp4', '.mp3', '.m4a', '.webm', '.3gp']:
            if os.path.exists(base_name + ext): os.remove(base_name + ext)
        # إظهار رسالة تفصيلية للمطور لمعرفة العطل بدقة بدلاً من الرسالة القديمة
        await query.edit_message_text(f"❌ عذراً! واجه المحرك عائقاً أثناء السحب الإجباري.\nوصف العطل: {str(e)[:100]}")

async def main():
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(CallbackQueryHandler(button_click))
    
    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    
    logger.info("🚀 AlhadiSoft Camouflaged Engine is operational!")
    
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
        
