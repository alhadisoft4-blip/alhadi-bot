import os
import asyncio
import logging
import threading
import http.server
import socketserver
import re
import json
import urllib.request
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

# 🔍 خوارزمية ذكية ومحصنة لاستخراج الـ Video ID من أي رابط يوتيوب بالعالم
def extract_youtube_id(url):
    # الطريقة الأولى: الفحص عبر الأنماط القياسية (بما فيها Shorts)
    match = re.search(r'(?:youtu\.be\/|youtube\.com\/(?:v\/|embed\/|watch\?v=|shorts\/)?)([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # الطريقة الثانية (الفحص العميق): تشريح الرابط والبحث عن المعرف المكون من 11 حرفاً كحائط صد أخير
    parts = re.split(r'[/\?=&]', url)
    for part in parts:
        if len(part) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', part):
            return part
    return None

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
        "🚀 مرحباً بك في محرك السحب اللامركزي المحصن - مؤسسة الهادي سوفت!\n\n👇 أرسل رابط الفيديو من (يوتيوب، فيسبوك، تيك توك) وسيتم فكه وسحبه فوراً.",
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
        await update.message.reply_text("🔄 المحرك اللامركزي نشط وجاهز، أرسل رابط الفيديو الآن.")
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

# 🛠️ محرك المعالجة الهجين المطور
def download_processor(url, is_audio, output_template):
    import yt_dlp
    
    # 💥 فك تشفير يوتيوب اللامركزي عبر الأنفاق المحدثة
    if "youtube.com" in url or "youtu.be" in url:
        logger.info("📺 YouTube URL detected! Running Bulletproof Extraction...")
        
        video_id = extract_youtube_id(url)
        if not video_id:
            raise Exception("لم يتمكن النظام من العثور على معرف فيديو صالح في الرابط المرسل.")
            
        logger.info(f"🎯 Target Video ID isolated successfully: {video_id}")
        
        # شبكة خوادم حليفة موسعة ومحدثة للتخلص من الضغط
        invidious_instances = [
            "https://invidious.privacydev.net",
            "https://iv.melmac.space",
            "https://invidious.perennialte.ch",
            "https://yt.artemislena.eu",
            "https://invidious.flokinet.to",
            "https://invidious.projectsegfau.lt",
            "https://invidious.slipfox.xyz",
            "https://iv.ggtyler.dev"
        ]
        
        direct_stream_url = None
        
        for instance in invidious_instances:
            try:
                api_url = f"{instance}/api/v1/videos/{video_id}"
                req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    
                    if is_audio:
                        adaptive = data.get("adaptiveFormats", [])
                        audio_streams = [f for f in adaptive if f.get("type", "").startswith("audio/")]
                        if audio_streams:
                            direct_stream_url = audio_streams[0].get("url")
                            break
                    else:
                        # جلب الفيديو المدمج الجاهز لتسريع السحب
                        streams = data.get("formatStreams", [])
                        mp4_streams = [f for f in streams if "mp4" in f.get("type", "")]
                        if mp4_streams:
                            direct_stream_url = mp4_streams[-1].get("url")
                            break
                        else:
                            # احتياطي في حال عدم وجود فيديو مدمج
                            adaptive = data.get("adaptiveFormats", [])
                            video_adaptive = [f for f in adaptive if f.get("type", "").startswith("video/mp4")]
                            if video_adaptive:
                                direct_stream_url = video_adaptive[0].get("url")
                                break
            except Exception as inst_err:
                logger.warning(f"Instance {instance} skipped: {inst_err}")
                continue 
                
        if not direct_stream_url:
            raise Exception("جميع أنفاق فك التشفير مضغوطة حالياً، أعد المحاولة بعد ثوانٍ.")
            
        url = direct_stream_url

    # 🌐 التنفيذ النهائي عبر yt-dlp للمقاطع الخام أو المنصات الأخرى
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
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
        await query.edit_message_text("🚀 جاري اختراق التشفير وسحب ملف الوسائط الخام...")
        
        filename = await loop.run_in_executor(None, download_processor, url, is_audio, output_template)
        final_file = f"{base_name}.mp3" if is_audio else filename
        
        if not os.path.exists(final_file) and not is_audio:
             final_file = base_name + ".mp4"
             
        await query.edit_message_text("⚡ اكتمل السحب اللامركزي بنجاح! جاري الرفع الفوري لـ تيليجرام...")
        
        with open(final_file, 'rb') as f:
            if is_audio:
                await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم استخراج الصوت بنجاح - الهادي سوفت")
            else:
                await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم كسر الحظر وتنزيل الفيديو بنجاح - الهادي سوفت")
        
        if os.path.exists(final_file): os.remove(final_file)
        user_urls.pop(chat_id, None)
        await query.delete_message()
        
    except Exception as e:
        logger.error(f"Engine Failure: {e}")
        for ext in ['.mp4', '.mp3', '.m4a', '.webm', '.3gp']:
            if os.path.exists(base_name + ext): os.remove(base_name + ext)
        await query.edit_message_text(f"❌ عذراً هندسة! واجه السيرفر عائقاً أثناء المعالجة.\nالوصف: {str(e)[:110]}")

async def main():
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(CallbackQueryHandler(button_click))
    
    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    
    logger.info("🚀 AlhadiSoft Bulletproof Decoupled Engine is operational!")
    
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
    
