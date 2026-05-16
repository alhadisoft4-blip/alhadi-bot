import os, asyncio, http.server, socketserver, threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

TOKEN = '8914679676:AAEbKf4zukBYg6Ibd7VsDSOSFPWCinPKRig'
user_urls = {}

PROXY_OPTIONS = {
    'quiet': True,
    'skip_download': True,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    'restrictfilenames': True
}

# خادم وهمي لإرضاء سيرفر ريندر المجاني ومنعه من إعطاء خطأ Port
def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [
        [KeyboardButton("🟢 Start"), KeyboardButton("🔴 Stop")],
        [KeyboardButton("👥 فريق الدعم الهادي سوفت"), KeyboardButton("📞 رقم الاتصال: 711129716")]
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(
        "🚀 أهلاً بك في بوت التحميل لمؤسسة الهادي سوفت!\n\n👇 استخدم الأزرار للتنقل أو أرسل الرابط مباشرة.",
        reply_markup=markup
    )

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.message.chat_id
    
    if text == "🟢 Start":
        await update.message.reply_text("🔄 البوت جاهز تماماً على السيرفر ومستعد لتلقي الروابط.")
        return
    elif text == "🔴 Stop":
        await update.message.reply_text("🛑 تم إيقاف العمليات الحالية.")
        return
    elif text == "👥 فريق الدعم الهادي سوفت":
        await update.message.reply_text("👋 مؤسسة الهادي سوفت لخدمات البرمجية وتطوير الأنظمة.")
        return
    elif text == "📞 رقم الاتصال: 711129716":
        await update.message.reply_text("📱 للتواصل المباشر أو الواتساب:\n👉 711129716")
        return

    if text.startswith("http://") or text.startswith("https://"):
        msg = await update.message.reply_text("⚡ جاري فحص الرابط وتجاوز القيود...")
        loop = asyncio.get_event_loop()
        try:
            with yt_dlp.YoutubeDL(PROXY_OPTIONS) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(text, download=False))
            title = info.get('title', 'Video')
            user_urls[chat_id] = text
            buttons = [
                [InlineKeyboardButton("🎬 جودة عالية", callback_data="high"), InlineKeyboardButton("🎬 جودة عادية", callback_data="low")],
                [InlineKeyboardButton("🎵 صوت MP3", callback_data="audio")]
            ]
            await msg.delete()
            await update.message.reply_text(f"📌 {title}\n\n👇 اختر الصيغة المطلوبة للتحميل:", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            await msg.edit_text("❌ فشل فحص الرابط. تأكد من جودة الإنترنت أو صلاحية الفيديو وحاول مجدداً.")
    else:
        await update.message.reply_text("⚠️ يرجى إرسال رابط صحيح أو استخدام أزرار التحكم.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id, choice = query.message.chat_id, query.data
    url = user_urls.get(chat_id)
    
    if not url:
        await query.edit_message_text("❌ انتهت الجلسة، يرجى إرسال الرابط مجدداً.")
        return
        
    await query.edit_message_text("📥 جاري تحميل الملف ومعالجته على السيرفر...")
    is_audio = (choice == "audio")
    fmt = 'bestaudio/best' if is_audio else ('bestvideo+bestaudio/best' if choice == "high" else 'worstvideo+worstaudio/worst')
    
    opts = {
        **PROXY_OPTIONS,
        'format': fmt, 
        'outtmpl': f'{chat_id}_file.%(ext)s', 
        'max_filesize': 48*1024*1024,
        'skip_download': False 
    }
    if is_audio:
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    else:
        opts['merge_output_format'] = 'mp4'

    loop = asyncio.get_event_loop()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            fn = ydl.prepare_filename(info)
            fn = os.path.splitext(fn)[0] + ('.mp3' if is_audio else '.mp4')
            
        await query.edit_message_text("🚀 اكتمل التحميل! جاري الرفع لتيليجرام...")
        with open(fn, 'rb') as f:
            if is_audio:
                await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم فصل الصوت بنجاح - الهادي سوفت")
            else:
                await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم تحميل الفيديو بنجاح - الهادي سوفت")
        if os.path.exists(fn): 
            os.remove(fn)
        user_urls.pop(chat_id, None)
    except Exception:
        await query.edit_message_text("❌ تعذر تحميل هذا الملف (قد يتجاوز حجمه 50 ميجا المسموحة للبوت).")

def main():
    # تشغيل السيرفر الوهمي في خلفية منفصلة لتجنب إغلاق السيرفر المجاني
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(CallbackQueryHandler(button_click))
    print("Bot is running successfully on Free Cloud VPS...")
    app.run_polling()

if __name__ == '__main__':
    main()