import os
import asyncio
import http.server
import socketserver
import threading
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError
import yt_dlp

TOKEN = '8914679676:AAEeV07KSkz_w5y-qbESc0BTFxB9d5LOvhA'
CHANNEL_ID = '@AlhadiSoft'
CHANNEL_INVITE_LINK = 'https://t.me/+BIHVdkbZ_qY5OTM0'

user_urls = {}

PROXY_OPTIONS = {
    'quiet': True,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'restrictfilenames': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'android', 'web'],
            'skip': ['dash', 'hls']
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'ar-YE,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    }
}

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"Web server routing active on port {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Web server notice: {e}")

async def is_subscribed(user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except TelegramError:
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await is_subscribed(user_id, context.bot):
        keyboard = [[InlineKeyboardButton("📢 اشترك في القناة هنا", url=CHANNEL_INVITE_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ عذراً! يجب عليك الاشتراك في قناة المؤسسة أولاً لتتمكن من استخدام البوت مجاناً.\n\n"
            "👇 اشترك عبر الرابط أدناه ثم أرسل /start مجدداً للتحقق والتشغيل:",
            reply_markup=reply_markup
        )
        return

    reply_keyboard = [
        [KeyboardButton("🟢 Start")],
        [KeyboardButton("💼 خدماتنا"), KeyboardButton("👥 فريق الدعم الهادي سوفت")]
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(
        "🚀 أهلاً بك مجدداً في بوت التحميل لمؤسسة الهادي سوفت!\n\n👇 استخدم الأزرار للتنقل أو أرسل رابط الفيديو مباشرة لبدء التحميل.",
        reply_markup=markup
    )

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.message.chat_id
    user_id = update.effective_user.id
    
    if not await is_subscribed(user_id, context.bot):
        keyboard = [[InlineKeyboardButton("📢 اشترك في القناة هنا", url=CHANNEL_INVITE_LINK)]]
        await update.message.reply_text(
            "⚠️ يرجى الاشتراك في القناة أولاً لتفعيل خدمات البوت:\n" + CHANNEL_INVITE_LINK,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if text == "🟢 Start":
        await update.message.reply_text("🔄 البوت نشط وجاهز تماماً، أرسل رابط الفيديو المُراد تحميله الآن.")
        return
    elif text == "💼 خدماتنا":
        await update.message.reply_text("🛠️ **خدمات مؤسسة الهادي سوفت:**\n\n👈 تطوير وترقية البوتات والأنظمة البرمجية بأحدث التقنيات السحابية العالمية.")
        return
    elif text == "👥 فريق الدعم الهادي سوفت":
        await update.message.reply_text(
            "👋 نحن فريق الهادي سوفت للبرمجيات، أخبرنا كيف يمكننا مساعدتك؟\n\n"
            "📥 للتواصل معنا مباشرة عبر الرابط التالي:\n"
            "👉 t.me/AlhadiSoft"
        )
        return

    if text.startswith("http://") or text.startswith("https://"):
        msg = await update.message.reply_text("⏳ نرجوا الانتظار طلبك قيد التقدم...")
        user_urls[chat_id] = text
        
        buttons = [
            [InlineKeyboardButton("🎬 جودة عالية (Best)", callback_data="high"), InlineKeyboardButton("🎬 جودة متوسطة (Medium)", callback_data="mid")],
            [InlineKeyboardButton("🎬 جودة عادية (Normal)", callback_data="low"), InlineKeyboardButton("🎬 جودة ضعيفة (Worst)", callback_data="worst")],
            [InlineKeyboardButton("🎵 تحويله إلى صوت MP3", callback_data="audio")]
        ]
        
        await msg.delete()
        await update.message.reply_text("📌 تم فحص الرابط بنجاح وتحضير مسارات السحب الرقمية!\n\n👇 اختر الجودة أو الصيغة المناسبة لبدء التحميل المباشر الآمن:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text("⚠️ يرجى إرسال رابط فيديو صحيح أو النقر على أحد أزرار الخدمات.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id, choice = query.message.chat_id, query.data
    url = user_urls.get(chat_id)
    
    if not url:
        await query.edit_message_text("❌ انتهت الجلسة البرمجية الحالية، يرجى إرسال الرابط مجدداً.")
        return
        
    await query.edit_message_text("📥 جاري كسر الحظر وسحب الملف من يوتيوب، يرجى الانتظار...")
    is_audio = (choice == "audio")
    
    # الخطة (أ): محاولة التحميل والرفع الذكي عبر المحرك الخارجي غير المحظور (الخيار الأسرع والأضمن لـ Render)
    api_url = "https://api.cobalt.tools/api/json"
    payload = {
        "url": url,
        "videoQuality": "720" if choice == "mid" else ("480" if choice == "low" else "1080"),
        "downloadMode": "audio" if is_audio else "video"
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers, timeout=25) as response:
                if response.status == 200:
                    res_data = await response.json()
                    file_dl_url = res_data.get("url")
                    if file_dl_url:
                        await query.edit_message_text("🚀 نجح السحب الخارجي! جاري إرسال الملف إلى حسابك...")
                        async with session.get(file_dl_url) as file_resp:
                            if file_resp.status == 200:
                                file_data = await file_resp.read()
                                fn = f"{chat_id}_download." + ("mp3" if is_audio else "mp4")
                                with open(fn, "wb") as f:
                                    f.write(file_data)
                                
                                with open(fn, 'rb') as f:
                                    if is_audio:
                                        await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم سحب وتحويل الصوت بنجاح - مؤسسة الهادي سوفت")
                                    else:
                                        await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم سحب الفيديو بنجاح وتخطي الحظر - مؤسسة الهادي سوفت")
                                if os.path.exists(fn):
                                    os.remove(fn)
                                user_urls.pop(chat_id, None)
                                return
    except Exception:
        pass # إذا فشل المحرك الخارجي ننتقل تلقائياً للمحرك المحلي الاحتياطي بالأسفل

    # الخطة (ب): التحميل المحلي الاحتياطي عبر السيرفر مع دمج محاكاة أجهزة iOS لفك حظر يوتيوب
    if choice == "audio":
        fmt = 'bestaudio/best'
    elif choice == "high":
        fmt = 'bestvideo+bestaudio/best'
    elif choice == "mid":
        fmt = 'bestvideo[height<=720]+bestaudio/best'
    elif choice == "low":
        fmt = 'bestvideo[height<=480]+bestaudio/best'
    else:
        fmt = 'worstvideo+worstaudio/worst'
        
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

    loop = asyncio.get_running_loop()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            fn = ydl.prepare_filename(info)
            fn = os.path.splitext(fn)[0] + ('.mp3' if is_audio else '.mp4')
            
        await query.edit_message_text("🚀 تم التحميل محلياً! جاري الرفع إلى تيليجرام...")
        with open(fn, 'rb') as f:
            if is_audio:
                await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم تحويل وفصل الصوت بنجاح - مؤسسة الهادي سوفت")
            else:
                await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم إحضار الفيديو بنجاح بالجودة المطلوبة - مؤسسة الهادي سوفت")
        if os.path.exists(fn): 
            os.remove(fn)
        user_urls.pop(chat_id, None)
    except Exception as e:
        print(f"All download attempts failed: {e}")
        await query.edit_message_text("❌ نعتذر! يوتيوب يحظر عمليات التحميل السحابية الكبيرة حالياً على السيرفر المجاني، أو أن حجم الفيديو يتعدى السعة القصوى للبوت (50 ميجا).")

async def main():
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("Bot startup sequence initialized successfully...")
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
        
