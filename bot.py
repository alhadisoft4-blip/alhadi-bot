import os
import asyncio
import logging
import threading
import http.server
import socketserver
import json
import urllib.request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError

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
        "🚀 محرك السحب السحابي المطور (الجيل الخامس) - مؤسسة الهادي سوفت جاهز للعمل!\n\n👇 أرسل رابط الفيديو من أي منصة (يوتيوب، فيسبوك، تيك توك، إلخ) للبث المباشر.",
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
        await update.message.reply_text("🔄 المحرك السحابي نشط، أرسل رابط الفيديو المُراد سحبه الآن.")
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
        await update.message.reply_text("📌 تم فحص الرابط بنجاح!\n\n👇 اختر صيغة الاستخراج المطلوبة:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text("⚠️ يرجى إرسال رابط فيديو صحيح يبدأ بـ http أو https.")

# 🛠️ دالة جلب الرابط المباشر وتحميله عبر محرك Cobalt العالمي السريع
def cobalt_fetch_and_download(video_url, is_audio, output_path):
    # مصفوفة سيرفرات Cobalt لضمان عدم توقف الخدمة أبداً
    cobalt_api_instances = [
        "https://api.cobalt.tools/api/json",
        "https://cobalt.api.v0.pw/api/json",
        "https://api.urlis.net/cobalt"
    ]
    
    payload = {
        "url": video_url,
        "videoQuality": "720",
        "audioFormat": "mp3",
        "isAudioOnly": is_audio,
        "filenamePattern": "basic"
    }
    
    data_bytes = json.dumps(payload).encode('utf-8')
    direct_download_url = None
    
    for api in cobalt_api_instances:
        try:
            req = urllib.request.Request(
                api, 
                data=data_bytes, 
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0'
                },
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                if res_data.get("status") in ["stream", "redirect"]:
                    direct_download_url = res_data.get("url")
                    break
        except Exception as e:
            logger.warning(f"Cobalt instance {api} failed: {e}")
            continue

    if not direct_download_url:
        raise Exception("فشلت جميع المحركات السحابية في معالجة الرابط، قد يكون المقطع خاص أو محظور.")

    # تحميل الملف الفعلي من الرابط المباشر النظيف إلى السيرفر
    logger.info(f"📥 Downloading direct media stream: {direct_download_url[:50]}...")
    download_req = urllib.request.Request(direct_download_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(download_req, timeout=60) as response:
        with open(output_path, 'wb') as out_file:
            out_file.write(response.read())
            
    return output_path

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    choice = query.data
    url = user_urls.get(chat_id)
    
    if not url:
        await query.edit_message_text("❌ انتهت الجلسة الأمنية، يرجى إعادة إرسال الرابط مجدداً.")
        return
        
    await query.edit_message_text("🔄 جاري إرسال الرابط لمحرك السحب السحابي المطور...")
    is_audio = (choice == "audio")
    
    ext = "mp3" if is_audio else "mp4"
    final_file = f"{chat_id}_hadi.{ext}"
    
    try:
        loop = asyncio.get_running_loop()
        await query.edit_message_text("🚀 جاري سحب وتخطي حظر المنصة (بدون كوكيز)...")
        
        await loop.run_in_executor(None, cobalt_fetch_and_download, url, is_audio, final_file)
             
        await query.edit_message_text("⚡ اكتمل السحب بنجاح! جاري الرفع الفوري لـ تيليجرام...")
        
        with open(final_file, 'rb') as f:
            if is_audio:
                await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم استخراج الصوت بنجاح - الهادي سوفت")
            else:
                await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم سحب الفيديو بنجاح - الهادي سوفت")
        
        if os.path.exists(final_file): os.remove(final_file)
        user_urls.pop(chat_id, None)
        await query.delete_message()
        
    except Exception as e:
        logger.error(f"Engine Failure: {e}")
        if os.path.exists(final_file): os.remove(final_file)
        await update.effective_message.reply_text(f"❌ عذراً هندسة! واجه البوت عائقاً.\nالوصف: {str(e)[:110]}")

async def main():
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(CallbackQueryHandler(button_click))
    
    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    
    logger.info("🚀 AlhadiSoft Cobalt Engine is operational!")
    
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
        
